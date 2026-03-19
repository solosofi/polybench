import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import GameAdapter


Position = Tuple[int, int]


class MiniRTSAdapter(GameAdapter):
    """Deterministic 11x11 grid RTS benchmark with a simple ruleset."""

    rows = 11
    cols = 11

    _city_positions: List[Position] = [
        (5, 5),
        (0, 0),
        (10, 0),
        (0, 10),
        (10, 10),
        (5, 0),
        (0, 5),
        (10, 5),
        (5, 10),
        (2, 2),
        (8, 2),
        (2, 8),
        (8, 8),
        (2, 5),
        (5, 2),
        (8, 5),
    ]

    def __init__(self, seed: int = 0, max_turns: int = 30) -> None:
        self.base_seed = seed
        self.max_turns = max_turns
        self.rng = random.Random(seed)
        self.turn = 1
        self.opponents = 1
        self.difficulty = "normal"
        self.players: Dict[int, Dict[str, Any]] = {}
        self.tiles: List[List[Dict[str, Any]]] = []
        self.cities: List[Dict[str, Any]] = []
        self.units: List[Dict[str, Any]] = []
        self._next_city_id = 1
        self._next_unit_id = 1

    def reset(self, difficulty: str, opponents: int, game_index: int) -> None:
        if opponents < 1:
            raise ValueError("MiniRTS requires at least 1 opponent")
        if opponents > 15:
            raise ValueError("MiniRTS supports up to 15 opponents on 11x11")

        self.difficulty = difficulty
        self.opponents = opponents
        seed = self.base_seed + game_index * 1009 + opponents * 37
        seed += {"easy": 0, "normal": 1, "hard": 2, "crazy": 3}.get(difficulty, 0) * 131
        self.rng = random.Random(seed)
        self.turn = 1
        self._next_city_id = 1
        self._next_unit_id = 1

        self._init_players()
        self._init_map()
        self._init_cities_and_units()
        self._place_terrain()

    def _init_players(self) -> None:
        bot_bonus = {"easy": -1, "normal": 0, "hard": 1, "crazy": 2}.get(
            self.difficulty, 0
        )
        self.players = {}
        for pid in range(self.opponents + 1):
            start_resources = 2
            if pid != 0:
                start_resources = max(0, start_resources + bot_bonus)
            self.players[pid] = {
                "resources": start_resources,
                "tech": set(),
                "move_range": 1,
            }

    def _init_map(self) -> None:
        self.tiles = []
        for _ in range(self.rows):
            row = []
            for _ in range(self.cols):
                row.append({"terrain": "plain", "resource": None})
            self.tiles.append(row)

    def _init_cities_and_units(self) -> None:
        self.cities = []
        self.units = []
        needed = self.opponents + 1
        positions = self._city_positions[:needed]
        for pid, (x, y) in enumerate(positions):
            city = {
                "id": self._next_city_id,
                "x": x,
                "y": y,
                "owner": pid,
                "income": 2,
                "farms": 0,
            }
            self._next_city_id += 1
            self.cities.append(city)

            unit = {
                "id": self._next_unit_id,
                "x": x,
                "y": y,
                "owner": pid,
                "type": "warrior",
                "hp": 10,
            }
            self._next_unit_id += 1
            self.units.append(unit)

    def _place_terrain(self) -> None:
        blocked = {(city["x"], city["y"]) for city in self.cities}
        candidates = [
            (x, y)
            for y in range(self.rows)
            for x in range(self.cols)
            if (x, y) not in blocked
        ]
        self.rng.shuffle(candidates)
        mountain_count = 10
        forest_count = 20
        for x, y in candidates[:mountain_count]:
            self.tiles[y][x]["terrain"] = "mountain"
        for x, y in candidates[mountain_count : mountain_count + forest_count]:
            if self.tiles[y][x]["terrain"] == "plain":
                self.tiles[y][x]["resource"] = "forest"

    def is_done(self) -> bool:
        if self.turn > self.max_turns:
            return True
        llm_cities = [c for c in self.cities if c["owner"] == 0]
        if not llm_cities:
            return True
        opponent_cities = [c for c in self.cities if c["owner"] != 0]
        if not opponent_cities:
            return True
        return False

    def get_state(self) -> Dict[str, Any]:
        tiles: List[List[Dict[str, Any]]] = []
        for y in range(self.rows):
            row: List[Dict[str, Any]] = []
            for x in range(self.cols):
                city = self._city_at(x, y)
                unit = self._unit_at(x, y)
                row.append(
                    {
                        "terrain": self.tiles[y][x]["terrain"],
                        "resource": self.tiles[y][x]["resource"],
                        "city_owner": None if not city else city["owner"],
                        "unit_owner": None if not unit else unit["owner"],
                    }
                )
            tiles.append(row)

        llm_player = self.players[0]
        return {
            "turn": self.turn,
            "player": "llm",
            "score": self._score_player(0),
            "resources": llm_player["resources"],
            "cities": [
                {
                    "id": c["id"],
                    "x": c["x"],
                    "y": c["y"],
                    "owner": c["owner"],
                    "income": c["income"],
                    "farms": c["farms"],
                }
                for c in self.cities
            ],
            "units": [
                {
                    "id": u["id"],
                    "x": u["x"],
                    "y": u["y"],
                    "owner": u["owner"],
                    "type": u["type"],
                    "hp": u["hp"],
                }
                for u in self.units
            ],
            "tech": sorted(llm_player["tech"]),
            "map": {"rows": self.rows, "cols": self.cols, "tiles": tiles},
        }

    def apply_action(self, action: Dict[str, Any], run_dir: str, turn_index: int) -> None:
        log = {
            "turn": self.turn,
            "action": action,
            "ok": False,
            "reason": "",
        }

        if not self.is_done():
            log["ok"], log["reason"] = self._apply_llm_action(action)
            self._run_bots()
            self._apply_income()
            self.turn += 1

        self._write_log(run_dir, turn_index, log)

    def get_result(self) -> Dict[str, Any]:
        llm_score = self._score_player(0)
        opponent_scores = [
            self._score_player(pid) for pid in self.players.keys() if pid != 0
        ]
        best_opponent = max(opponent_scores) if opponent_scores else 0

        if not [c for c in self.cities if c["owner"] == 0]:
            result = "loss"
        elif not [c for c in self.cities if c["owner"] != 0]:
            result = "win"
        elif llm_score > best_opponent:
            result = "win"
        elif llm_score < best_opponent:
            result = "loss"
        else:
            result = "draw"

        return {"result": result, "score": llm_score}

    def _write_log(self, run_dir: str, turn_index: int, log: Dict[str, Any]) -> None:
        if not run_dir:
            return
        path = Path(run_dir) / f"turn_{turn_index:03d}_minirts_log.json"
        path.write_text(json_dumps(log), encoding="utf-8")

    def _apply_llm_action(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        action_type = action.get("type")
        if action_type == "end_turn":
            return True, "end_turn"
        if action_type == "move":
            return self._apply_move(action)
        if action_type == "attack":
            return self._apply_attack(action)
        if action_type == "train":
            return self._apply_train(action)
        if action_type == "build":
            return self._apply_build(action)
        if action_type == "research":
            return self._apply_research(action)
        return False, "unsupported action"

    def _apply_move(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        src = self._pos(action.get("unit_id") or action.get("from"))
        dst = self._pos(action.get("to"))
        if src is None or dst is None:
            return False, "missing position"
        unit = self._unit_at(*src)
        if not unit or unit["owner"] != 0:
            return False, "unit not found"
        if not self._in_bounds(dst) or not self._is_passable(dst):
            return False, "invalid destination"
        if self._unit_at(*dst):
            return False, "destination occupied"

        move_range = self.players[0]["move_range"]
        if self._manhattan(src, dst) > move_range:
            return False, "out of range"

        city = self._city_at(*dst)
        if city and city["owner"] != 0:
            city["owner"] = 0

        unit["x"], unit["y"] = dst
        return True, "moved"

    def _apply_attack(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        src = self._pos(action.get("unit_id") or action.get("from"))
        target = self._pos(action.get("target"))
        if src is None or target is None:
            return False, "missing position"
        unit = self._unit_at(*src)
        if not unit or unit["owner"] != 0:
            return False, "unit not found"

        attack_range = 1
        if unit["type"] == "archer":
            attack_range = 2
        if self._manhattan(src, target) > attack_range:
            return False, "target out of range"

        enemy_unit = self._unit_at(*target)
        if enemy_unit and enemy_unit["owner"] != 0:
            self.units.remove(enemy_unit)
            return True, "unit destroyed"

        city = self._city_at(*target)
        if city and city["owner"] != 0:
            city["owner"] = 0
            return True, "city captured"

        return False, "no enemy at target"

    def _apply_train(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        city_pos = self._pos(action.get("city_id"))
        if city_pos is None:
            return False, "missing city"
        city = self._city_at(*city_pos)
        if not city or city["owner"] != 0:
            return False, "city not owned"
        if self._unit_at(*city_pos):
            return False, "city occupied"

        unit_type = action.get("unit_type", "warrior")
        cost = 2
        if unit_type == "archer":
            if "archery" not in self.players[0]["tech"]:
                return False, "archery not researched"
            cost = 3
        elif unit_type != "warrior":
            return False, "unknown unit_type"

        if self.players[0]["resources"] < cost:
            return False, "insufficient resources"
        self.players[0]["resources"] -= cost
        unit = {
            "id": self._next_unit_id,
            "x": city_pos[0],
            "y": city_pos[1],
            "owner": 0,
            "type": unit_type,
            "hp": 10,
        }
        self._next_unit_id += 1
        self.units.append(unit)
        return True, "unit trained"

    def _apply_build(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        city_pos = self._pos(action.get("city_id"))
        if city_pos is None:
            return False, "missing city"
        city = self._city_at(*city_pos)
        if not city or city["owner"] != 0:
            return False, "city not owned"
        building = action.get("building_type")
        if building != "farm":
            return False, "unknown building_type"
        if self.players[0]["resources"] < 1:
            return False, "insufficient resources"

        self.players[0]["resources"] -= 1
        city["income"] += 1
        city["farms"] += 1

        forest = self._adjacent_forest(city_pos)
        if forest:
            fx, fy = forest
            self.tiles[fy][fx]["resource"] = None
        return True, "farm built"

    def _apply_research(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        tech = action.get("tech")
        if tech not in {"riding", "archery", "farming"}:
            return False, "unknown tech"
        if tech in self.players[0]["tech"]:
            return False, "already researched"
        cost = 4
        if self.players[0]["resources"] < cost:
            return False, "insufficient resources"
        self.players[0]["resources"] -= cost
        self.players[0]["tech"].add(tech)
        if tech == "riding":
            self.players[0]["move_range"] = 2
        return True, "researched"

    def _run_bots(self) -> None:
        for pid in range(1, self.opponents + 1):
            self._bot_turn(pid)

    def _bot_turn(self, pid: int) -> None:
        if not [c for c in self.cities if c["owner"] == pid]:
            return

        units = sorted([u for u in self.units if u["owner"] == pid], key=_unit_key)
        for unit in units:
            target = self._adjacent_enemy_unit(unit, target_owner=0)
            if target:
                self.units.remove(target)
                return

        for unit in units:
            city = self._adjacent_enemy_city(unit, target_owner=0)
            if city:
                unit["x"], unit["y"] = city["x"], city["y"]
                city["owner"] = pid
                return

        if self.players[pid]["resources"] >= 2:
            city = self._first_city(pid)
            if city and not self._unit_at(city["x"], city["y"]):
                self.players[pid]["resources"] -= 2
                unit = {
                    "id": self._next_unit_id,
                    "x": city["x"],
                    "y": city["y"],
                    "owner": pid,
                    "type": "warrior",
                    "hp": 10,
                }
                self._next_unit_id += 1
                self.units.append(unit)
                return

        if not units:
            return
        unit = units[0]
        target_city = self._nearest_city(unit, owner=0)
        if not target_city:
            return
        step = self._step_towards((unit["x"], unit["y"]), (target_city["x"], target_city["y"]))
        if step and self._is_passable(step) and not self._unit_at(*step):
            city = self._city_at(*step)
            if city and city["owner"] != pid:
                city["owner"] = pid
            unit["x"], unit["y"] = step

    def _apply_income(self) -> None:
        for pid, player in self.players.items():
            income = sum(c["income"] for c in self.cities if c["owner"] == pid)
            player["resources"] += income

    def _score_player(self, pid: int) -> int:
        cities = len([c for c in self.cities if c["owner"] == pid])
        units = len([u for u in self.units if u["owner"] == pid])
        resources = int(self.players[pid]["resources"])
        tech = len(self.players[pid]["tech"])
        return cities * 100 + units * 10 + resources + tech * 5

    def _city_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        for city in self.cities:
            if city["x"] == x and city["y"] == y:
                return city
        return None

    def _unit_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        for unit in self.units:
            if unit["x"] == x and unit["y"] == y:
                return unit
        return None

    def _adjacent_enemy_unit(
        self, unit: Dict[str, Any], target_owner: int
    ) -> Optional[Dict[str, Any]]:
        for nx, ny in self._neighbors(unit["x"], unit["y"]):
            enemy = self._unit_at(nx, ny)
            if enemy and enemy["owner"] == target_owner:
                return enemy
        return None

    def _adjacent_enemy_city(
        self, unit: Dict[str, Any], target_owner: int
    ) -> Optional[Dict[str, Any]]:
        for nx, ny in self._neighbors(unit["x"], unit["y"]):
            city = self._city_at(nx, ny)
            if city and city["owner"] == target_owner:
                return city
        return None

    def _adjacent_forest(self, pos: Position) -> Optional[Position]:
        for nx, ny in self._neighbors(pos[0], pos[1]):
            tile = self.tiles[ny][nx]
            if tile["resource"] == "forest":
                return (nx, ny)
        return None

    def _first_city(self, owner: int) -> Optional[Dict[str, Any]]:
        for city in sorted(self.cities, key=_city_key):
            if city["owner"] == owner:
                return city
        return None

    def _nearest_city(self, unit: Dict[str, Any], owner: int) -> Optional[Dict[str, Any]]:
        cities = [c for c in self.cities if c["owner"] == owner]
        if not cities:
            return None
        ux, uy = unit["x"], unit["y"]
        return min(cities, key=lambda c: abs(c["x"] - ux) + abs(c["y"] - uy))

    def _step_towards(self, src: Position, dst: Position) -> Optional[Position]:
        sx, sy = src
        dx = 0
        dy = 0
        if dst[0] > sx:
            dx = 1
        elif dst[0] < sx:
            dx = -1
        if dst[1] > sy:
            dy = 1
        elif dst[1] < sy:
            dy = -1

        candidates = []
        if dx != 0:
            candidates.append((sx + dx, sy))
        if dy != 0:
            candidates.append((sx, sy + dy))
        for pos in candidates:
            if self._in_bounds(pos) and self._is_passable(pos):
                return pos
        return None

    def _neighbors(self, x: int, y: int) -> List[Position]:
        candidates = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
        return [pos for pos in candidates if self._in_bounds(pos)]

    def _in_bounds(self, pos: Position) -> bool:
        x, y = pos
        return 0 <= x < self.cols and 0 <= y < self.rows

    def _is_passable(self, pos: Position) -> bool:
        x, y = pos
        return self.tiles[y][x]["terrain"] != "mountain"

    def _pos(self, value: Any) -> Optional[Position]:
        if value is None:
            return None
        if isinstance(value, dict) and "x" in value and "y" in value:
            return int(value["x"]), int(value["y"])
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return int(value[0]), int(value[1])
        if isinstance(value, str) and "," in value:
            xs, ys = value.split(",", 1)
            return int(xs.strip()), int(ys.strip())
        return None

    @staticmethod
    def _manhattan(a: Position, b: Position) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _city_key(city: Dict[str, Any]) -> Tuple[int, int]:
    return city["y"], city["x"]


def _unit_key(unit: Dict[str, Any]) -> Tuple[int, int]:
    return unit["y"], unit["x"]


def json_dumps(data: Dict[str, Any]) -> str:
    import json

    return json.dumps(data, indent=2)
