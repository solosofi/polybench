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
  "game_path": "C:/Users/User/Documents/PolytopiaBench/game/Polytopia.exe",
  "start_wait_sec": 8,
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
  "start_flow": [
    "main_play",
    "perfection",
    "difficulty",
    "opponents",
    "start_game"
  ],
  "start_buttons": {
    "main_play": [960, 540],
    "perfection": [960, 620],
    "difficulty_easy": [400, 500],
    "difficulty_normal": [600, 500],
    "difficulty_hard": [800, 500],
    "difficulty_crazy": [1000, 500],
    "opponents_1": [500, 700],
    "opponents_7": [800, 700],
    "opponents_15": [1100, 700],
    "start_game": [960, 900]
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
Use `examples/capture_mouse_pos.py` to grab screen coordinates.

### Auto-start behavior

If `game_path` is set, the benchmark will launch Polytopia and click the
`start_flow` sequence automatically. The special steps `"difficulty"` and
`"opponents"` are replaced at runtime using the CLI values, and they map to
`start_buttons` keys like `difficulty_easy`, `opponents_7`.

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

## Kaggle LLM Bridge (remote)

You can run the LLM inside a Kaggle notebook and call it over HTTP from your
Windows machine (where Polytopia + UI automation runs).

### Kaggle notebook

1) Open a Kaggle notebook with `kaggle-benchmarks` available.
2) Create a cell with the bridge server:

```python
!pip -q install kaggle-benchmarks

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import kaggle_benchmarks as kbench

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/prompt":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        data = json.loads(body.decode("utf-8"))
        prompt = data.get("prompt", "")
        model = data.get("model")
        llm = kbench.llm if not model else kbench.llms[model]
        response = llm.prompt(prompt)
        payload = json.dumps({"content": response}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

server = HTTPServer(("0.0.0.0", 8000), Handler)
server.serve_forever()
```

3) Expose port 8000 with a tunnel (ngrok or cloudflared) and copy the public URL.

### Windows run (using Kaggle LLM)

```powershell
polybench run --difficulty hard --opponents 7 --games 1 --calibration calibration.json ^
  --llm-provider kaggle ^
  --llm-host https://YOUR_TUNNEL_URL ^
  --llm-model google/gemini-2.5-flash
```

If `--llm-model` is omitted, the bridge uses Kaggle’s default `kbench.llm`.

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
- `--llm-provider` openai | kaggle
- `--llm-host` HTTP base URL (OpenAI-compatible `/v1/chat/completions`)
- `--llm-model` model name for HTTP LLM
- `--llm-api-key` API key for HTTP LLM (or set `POLYBENCH_LLM_API_KEY`)
- `--k-factor` ELO K (default 32)
- `--opponent-elo` (default 1000)
- `--start-elo` (default 1000)
