# Polytopia LLM Benchmark

Fully automated UI benchmark for The Battle of Polytopia (Perfection mode, strict 30 actions).  
It captures the screen, OCRs game state, clicks actions, and reads the final score from the game.

## Install

```powershell
pip install polytopia-bench
```

Requirements:
- Windows
- Tesseract OCR installed (set `tesseract_cmd` in `calibration.json` if not on PATH)

## Calibration (one-time)

Create `calibration.json` with your UI coordinates and grid settings. Minimal example:

```json
{
  "window_title": "The Battle of Polytopia",
  "tesseract_cmd": "C:/Program Files/Tesseract-OCR/tesseract.exe",
  "regions": {
    "turn": [10, 10, 120, 40],
    "score": [1700, 10, 200, 40],
    "map": [200, 120, 1500, 800],
    "end_screen": [600, 200, 700, 500]
  },
  "tile_grid": {
    "origin": [260, 170],
    "dx": 64,
    "dy": 56,
    "rows": 11,
    "cols": 11
  },
  "buttons": {
    "end_turn": [1780, 960],
    "confirm": [1200, 900],
    "close_popup": [1700, 120],
    "tech_tree": [80, 960]
  },
  "unit_buttons": {
    "warrior": [600, 900]
  },
  "build_buttons": {
    "farm": [600, 900]
  },
  "tech_buttons": {
    "riding": [900, 500]
  },
  "result_rules": {
    "win_score": 1
  }
}
```

Use `examples/calibration_template.json` as a starting point.

## Run

```powershell
polybench run --difficulty easy --opponents 1 --games 1 --calibration calibration.json
```

LLM command (stdin prompt → stdout JSON):

```powershell
polybench run --difficulty hard --opponents 7 --games 1 --calibration calibration.json --llm-cmd "python examples\\echo_llm.py"
```

OpenAI-compatible HTTP endpoint:

```powershell
polybench run --difficulty hard --opponents 7 --games 1 --calibration calibration.json --llm-host http://localhost:8000 --llm-model your-model --llm-api-key YOUR_KEY
```

Env alternative:

```powershell
$env:POLYBENCH_LLM_HOST = "http://localhost:8000"
$env:POLYBENCH_LLM_MODEL = "your-model"
$env:POLYBENCH_LLM_API_KEY = "YOUR_KEY"
polybench run --difficulty hard --opponents 7 --games 1 --calibration calibration.json
```

## Python API

```python
import polybench

cfg = polybench.RunConfig(
    difficulty="easy",
    opponents=1,
    games=1,
    calibration_path="calibration.json",
    llm_host="http://localhost:8000",
    llm_model="your-model",
    llm_api_key="YOUR_KEY",
)
polybench.run_benchmark(cfg)
```

## Game API

```python
from polybench import UIAutomationGameAPI

api = UIAutomationGameAPI("calibration.json")
api.reset("easy", 1, 1)
state = api.get_state()
# ...call your LLM and produce an action...
# api.apply_action(action, run_dir="runs/tmp", turn_index=1)
```

## How it works

- Captures screen → OCRs `turn` and `score` → samples a color grid for the map.
- Builds prompt → LLM returns JSON action.
- Clicks UI to execute the action.
- Stops after 30 actions (Perfection limit), then reads the final score and writes summary.

## Action schema

Allowed action types:
- `end_turn`
- `move`
- `attack`
- `train`
- `build`
- `research`

For UI automation, `unit_id` and `city_id` must be coordinates:

```json
{ "type": "move", "unit_id": { "x": 3, "y": 5 }, "to": { "x": 4, "y": 5 } }
```

## Output

Each run writes:
- `runs/<timestamp>_<difficulty>_<opponents>/game_###/turn_###_prompt.txt`
- `runs/<timestamp>_<difficulty>_<opponents>/game_###/turn_###_response.txt`
- `runs/<timestamp>_<difficulty>_<opponents>/game_###/turn_###_action.json`
- `runs/<timestamp>_<difficulty>_<opponents>/game_###/turn_###_ui_log.txt`
- `runs/<timestamp>_<difficulty>_<opponents>/summary.json`

## Options

`polybench run` supports:
- `--difficulty` easy | normal | hard | crazy
- `--opponents` 1 | 7 | 15
- `--games` (default 1)
- `--calibration` path to calibration.json
- `--llm-cmd` external command that reads prompt on stdin and returns JSON on stdout
- `--llm-host` HTTP base URL (OpenAI-compatible `/v1/chat/completions`)
- `--llm-model` model name for HTTP LLM
- `--llm-api-key` API key for HTTP LLM (or set `POLYBENCH_LLM_API_KEY`)
- `--k-factor` ELO K (default 32)
- `--opponent-elo` (default 1000)
- `--start-elo` (default 1000)
