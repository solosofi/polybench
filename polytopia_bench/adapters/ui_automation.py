import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import mss
    import pyautogui
    import pytesseract
    from PIL import Image
except Exception as exc:  # pragma: no cover - runtime dependency check
    raise ImportError(
        "UI automation requires mss, pyautogui, pytesseract, and Pillow. "
        "Install via: pip install polytopia-bench"
    ) from exc

from .base import GameAdapter


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class UIAutomationAdapter(GameAdapter):
    def __init__(self, calibration_path: str = "calibration.json") -> None:
        self.calibration_path = Path(calibration_path)
        self.calibration: Dict[str, Any] = {}
        self._sct: Optional[mss.mss] = None
        self._game_proc: Optional[subprocess.Popen] = None

    def _load_calibration(self) -> None:
        if not self.calibration_path.exists():
            raise FileNotFoundError(
                "Missing calibration.json. Create one with UI coordinates "
                "for your resolution and layout."
            )
        data = json.loads(self.calibration_path.read_text(encoding="utf-8"))
        self._validate_calibration(data)
        self.calibration = data
        tesseract_cmd = self.calibration.get("tesseract_cmd")
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self._sct = mss.mss()
        self._focus_window()

    def _focus_window(self) -> None:
        title = self.calibration.get("window_title")
        if not title:
            return
        try:
            windows = pyautogui.getWindowsWithTitle(title)
            if windows:
                windows[0].activate()
                time.sleep(0.5)
        except Exception:
            return

    def _validate_calibration(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ValueError("calibration.json must be a JSON object")
        regions = data.get("regions", {})
        required_regions = ["turn", "score", "map", "end_screen"]
        for name in required_regions:
            self._require_region(regions, name)
        tile_grid = data.get("tile_grid", {})
        self._require_point(tile_grid, "origin")
        for key in ("dx", "dy", "rows", "cols"):
            if key not in tile_grid:
                raise ValueError(f"tile_grid missing {key}")
        buttons = data.get("buttons", {})
        self._require_point(buttons, "end_turn")
        if data.get("game_path"):
            start_flow = data.get("start_flow")
            start_buttons = data.get("start_buttons")
            if not isinstance(start_flow, list) or not start_flow:
                raise ValueError("start_flow must be a non-empty list when game_path is set")
            if not isinstance(start_buttons, dict) or not start_buttons:
                raise ValueError("start_buttons must be provided when game_path is set")

    @staticmethod
    def _require_region(container: Dict[str, Any], name: str) -> None:
        value = container.get(name)
        if not (isinstance(value, list) and len(value) == 4):
            raise ValueError(f"Region '{name}' must be [x,y,w,h]")

    @staticmethod
    def _require_point(container: Dict[str, Any], name: str) -> None:
        value = container.get(name)
        if not (isinstance(value, list) and len(value) == 2):
            raise ValueError(f"Point '{name}' must be [x,y]")

    def _region(self, name: str) -> Tuple[int, int, int, int]:
        x, y, w, h = self.calibration["regions"][name]
        return int(x), int(y), int(w), int(h)

    def _point(self, value: List[Any]) -> Tuple[int, int]:
        return int(value[0]), int(value[1])

    def _screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        if self._sct is None:
            raise RuntimeError("Calibration not loaded")
        if region is None:
            monitor = self._sct.monitors[0]
        else:
            x, y, w, h = region
            monitor = {"left": x, "top": y, "width": w, "height": h}
        grab = self._sct.grab(monitor)
        return Image.frombytes("RGB", grab.size, grab.rgb)

    def _ocr_text(self, image: Image.Image) -> str:
        gray = image.convert("L")
        return pytesseract.image_to_string(gray, config="--psm 7").strip()

    def _ocr_int(self, region_name: str) -> Optional[int]:
        image = self._screenshot(self._region(region_name))
        text = self._ocr_text(image)
        digits = re.findall(r"\d+", text)
        if not digits:
            return None
        return int("".join(digits))

    def _tile_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        grid = self.calibration["tile_grid"]
        ox, oy = self._point(grid["origin"])
        dx = int(grid["dx"])
        dy = int(grid["dy"])
        return ox + x * dx, oy + y * dy

    @staticmethod
    def _sleep_short() -> None:
        time.sleep(0.25)

    def _click(self, point: Tuple[int, int], log: Optional[Path] = None, label: str = "") -> None:
        x, y = point
        pyautogui.click(x, y)
        if log:
            with log.open("a", encoding="utf-8") as handle:
                handle.write(f"click {label} @ {x},{y}\n")

    def _parse_xy(self, value: Any, label: str) -> Tuple[int, int]:
        if isinstance(value, dict):
            return int(value["x"]), int(value["y"])
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return int(value[0]), int(value[1])
        if isinstance(value, str) and "," in value:
            x_str, y_str = value.split(",", 1)
            return int(x_str.strip()), int(y_str.strip())
        raise ValueError(f"{label} must be {{x,y}} or 'x,y'")

    def _start_game(self, difficulty: str, opponents: int) -> None:
        game_path = self.calibration.get("game_path")
        if not game_path:
            return

        if self._game_proc is None or self._game_proc.poll() is not None:
            self._game_proc = subprocess.Popen([game_path])
            time.sleep(float(self.calibration.get("start_wait_sec", 8.0)))

        self._focus_window()

        start_buttons = self.calibration.get("start_buttons", {})
        start_flow = self.calibration.get("start_flow", [])
        for step in start_flow:
            if step == "difficulty":
                key = f"difficulty_{difficulty}"
            elif step == "opponents":
                key = f"opponents_{opponents}"
            else:
                key = step
            if key not in start_buttons:
                raise ValueError(f"start_buttons missing '{key}'")
            self._click(self._point(start_buttons[key]))
            self._sleep_short()

    def reset(self, difficulty: str, opponents: int, game_index: int) -> None:
        _ = difficulty
        _ = opponents
        _ = game_index
        self._load_calibration()
        self._start_game(difficulty, opponents)

    def is_done(self) -> bool:
        text = self._ocr_text(self._screenshot(self._region("end_screen"))).lower()
        return any(k in text for k in ("score", "game over", "victory", "defeat"))

    def get_state(self) -> Dict[str, Any]:
        turn = self._ocr_int("turn")
        score = self._ocr_int("score")

        grid = self.calibration["tile_grid"]
        rows = int(grid["rows"])
        cols = int(grid["cols"])
        screen = self._screenshot()

        samples: List[List[str]] = []
        for y in range(rows):
            row: List[str] = []
            for x in range(cols):
                px, py = self._tile_to_screen(x, y)
                try:
                    r, g, b = screen.getpixel((px, py))
                    row.append(f"#{r:02x}{g:02x}{b:02x}")
                except Exception:
                    row.append("#000000")
            samples.append(row)

        return {
            "turn": turn or 0,
            "player": "llm",
            "score": score,
            "cities": [],
            "units": [],
            "tech": [],
            "map": {
                "rows": rows,
                "cols": cols,
                "samples": samples,
            },
        }

    def apply_action(self, action: Dict[str, Any], run_dir: str, turn_index: int) -> None:
        log_path = Path(run_dir) / f"turn_{turn_index:03d}_ui_log.txt"
        log_path.write_text("", encoding="utf-8")

        buttons = self.calibration.get("buttons", {})
        action_type = action.get("type")
        print(f"UI action: {action}")

        def click_button(name: str) -> None:
            if name not in buttons:
                raise ValueError(f"Button '{name}' not in calibration.json")
            self._click(self._point(buttons[name]), log_path, name)
            self._sleep_short()

        if action_type == "end_turn":
            click_button("end_turn")
            return

        if action_type in ("move", "attack"):
            src_value = action.get("from") or action.get("unit_id")
            if src_value is None:
                raise ValueError("move/attack requires unit_id or from")
            src = self._parse_xy(src_value, "unit_id")
            dst_value = action.get("to") if action_type == "move" else action.get("target")
            if dst_value is None:
                raise ValueError("move requires to, attack requires target")
            dst = self._parse_xy(dst_value, "to/target")
            self._click(self._tile_to_screen(src[0], src[1]), log_path, "unit")
            self._sleep_short()
            self._click(self._tile_to_screen(dst[0], dst[1]), log_path, "dest")
            if "confirm" in buttons:
                click_button("confirm")
            if "close_popup" in buttons:
                click_button("close_popup")
            return

        if action_type == "train":
            city = self._parse_xy(action.get("city_id"), "city_id")
            unit_type = action.get("unit_type")
            unit_buttons = self.calibration.get("unit_buttons", {})
            if unit_type not in unit_buttons:
                raise ValueError(f"unit_type '{unit_type}' missing in calibration.json")
            self._click(self._tile_to_screen(city[0], city[1]), log_path, "city")
            self._sleep_short()
            self._click(self._point(unit_buttons[unit_type]), log_path, unit_type)
            if "confirm" in buttons:
                click_button("confirm")
            if "close_popup" in buttons:
                click_button("close_popup")
            return

        if action_type == "build":
            city = self._parse_xy(action.get("city_id"), "city_id")
            building_type = action.get("building_type")
            build_buttons = self.calibration.get("build_buttons", {})
            if building_type not in build_buttons:
                raise ValueError(
                    f"building_type '{building_type}' missing in calibration.json"
                )
            self._click(self._tile_to_screen(city[0], city[1]), log_path, "city")
            self._sleep_short()
            self._click(self._point(build_buttons[building_type]), log_path, building_type)
            if "confirm" in buttons:
                click_button("confirm")
            if "close_popup" in buttons:
                click_button("close_popup")
            return

        if action_type == "research":
            tech = action.get("tech")
            tech_buttons = self.calibration.get("tech_buttons", {})
            if "tech_tree" not in buttons:
                raise ValueError("buttons.tech_tree missing in calibration.json")
            if tech not in tech_buttons:
                raise ValueError(f"tech '{tech}' missing in calibration.json")
            click_button("tech_tree")
            self._click(self._point(tech_buttons[tech]), log_path, tech)
            if "confirm" in buttons:
                click_button("confirm")
            if "close_popup" in buttons:
                click_button("close_popup")
            return

        raise ValueError(f"Unsupported action type: {action_type}")

    def get_result(self) -> Dict[str, Any]:
        score = self._ocr_int("score")
        end_text = self._ocr_text(self._screenshot(self._region("end_screen"))).lower()

        result = "win"
        if "defeat" in end_text or "loss" in end_text:
            result = "loss"
        elif "draw" in end_text:
            result = "draw"
        else:
            rules = self.calibration.get("result_rules", {})
            win_score = rules.get("win_score")
            draw_score = rules.get("draw_score")
            if win_score is not None and score is not None:
                result = "win" if score >= win_score else "loss"
            if draw_score is not None and score is not None and win_score is not None:
                if score >= draw_score and score < win_score:
                    result = "draw"

        return {"result": result, "score": score}
