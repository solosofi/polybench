# MiniRTS LLM Benchmark

Deterministic 11x11 grid RTS benchmark for LLMs.  
No OCR, no UI automation, fast and reproducible.  
Strict 30 action cap.

## Install

```powershell
pip install mirts-bench
```

## Run

```powershell
polybench run --difficulty hard --opponents 7 --games 1
```

LLM command (stdin prompt → stdout JSON):

```powershell
polybench run --difficulty hard --opponents 7 --games 1 --llm-cmd "python examples\\echo_llm.py"
```

OpenAI-compatible HTTP endpoint:

```powershell
polybench run --difficulty hard --opponents 7 --games 1 --llm-host http://localhost:8000 --llm-model your-model --llm-api-key YOUR_KEY
```

Env alternative:

```powershell
$env:POLYBENCH_LLM_HOST = "http://localhost:8000"
$env:POLYBENCH_LLM_MODEL = "your-model"
$env:POLYBENCH_LLM_API_KEY = "YOUR_KEY"
polybench run --difficulty hard --opponents 7 --games 1
```

## Kaggle (local, no ngrok)

Run inside a Kaggle notebook with `kaggle-benchmarks` available.

```python
!pip -q install kaggle-benchmarks mirts-bench

!polybench run --difficulty hard --opponents 7 --games 1 --llm-provider kaggle --llm-model google/gemini-2.5-flash
```

If `--llm-model` is omitted, the default Kaggle LLM is used.

## Python API

```python
import polybench

cfg = polybench.RunConfig(
    difficulty="easy",
    opponents=1,
    games=1,
    llm_host="http://localhost:8000",
    llm_model="your-model",
    llm_api_key="YOUR_KEY",
)
polybench.run_benchmark(cfg)
```

## How it works

- Generates a deterministic 11x11 grid with cities, resources, and blockers.
- Builds a prompt from the current state.
- LLM returns a JSON action.
- The engine applies the action and advances the turn.
- Stops after 30 actions and scores the result.

## Action schema

Allowed action types:
- `end_turn`
- `move`
- `attack`
- `train`
- `build`
- `research`

Unit and city identifiers are grid coordinates:

```json
{ "type": "move", "unit_id": { "x": 3, "y": 5 }, "to": { "x": 4, "y": 5 } }
```

## Output

Each run writes:
- `runs/<timestamp>_<difficulty>_<opponents>/game_###/turn_###_prompt.txt`
- `runs/<timestamp>_<difficulty>_<opponents>/game_###/turn_###_response.txt`
- `runs/<timestamp>_<difficulty>_<opponents>/game_###/turn_###_action.json`
- `runs/<timestamp>_<difficulty>_<opponents>/summary.json`

## Options

`polybench run` supports:
- `--difficulty` easy | normal | hard | crazy
- `--opponents` 1 | 7 | 15
- `--games` (default 1)
- `--llm-cmd` external command that reads prompt on stdin and returns JSON on stdout
- `--llm-provider` openai | kaggle
- `--llm-host` HTTP base URL (OpenAI-compatible `/v1/chat/completions`)
- `--llm-model` model name for HTTP LLM
- `--llm-api-key` API key for HTTP LLM (or set `POLYBENCH_LLM_API_KEY`)
- `--k-factor` ELO K (default 32)
- `--opponent-elo` (default 1000)
- `--start-elo` (default 1000)
