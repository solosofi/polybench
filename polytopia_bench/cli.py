import argparse
import os
import shlex
from typing import List, Optional

from .benchmark import RunConfig, run_benchmark


def _parse_llm_cmd(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    return shlex.split(value, posix=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="polytopia_bench")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the benchmark")
    run.add_argument("--difficulty", choices=["easy", "normal", "hard", "crazy"], required=True)
    run.add_argument("--opponents", type=int, choices=[1, 7, 15], required=True)
    run.add_argument("--games", type=int, default=1)
    run.add_argument("--calibration", type=str, default="calibration.json")
    run.add_argument("--llm-cmd", type=str, default=None)
    run.add_argument("--llm-host", type=str, default=None)
    run.add_argument("--llm-model", type=str, default=None)
    run.add_argument("--llm-api-key", type=str, default=None)
    run.add_argument("--k-factor", type=float, default=32.0)
    run.add_argument("--opponent-elo", type=float, default=1000.0)
    run.add_argument("--start-elo", type=float, default=1000.0)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        if args.games < 1:
            raise SystemExit("--games must be >= 1")
        llm_cmd = _parse_llm_cmd(args.llm_cmd)
        llm_host = args.llm_host or os.getenv("POLYBENCH_LLM_HOST")
        llm_model = args.llm_model or os.getenv("POLYBENCH_LLM_MODEL")
        llm_api_key = args.llm_api_key or os.getenv("POLYBENCH_LLM_API_KEY")
        config = RunConfig(
            difficulty=args.difficulty,
            opponents=args.opponents,
            games=args.games,
            calibration_path=args.calibration,
            llm_cmd=llm_cmd,
            llm_host=llm_host,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            k_factor=args.k_factor,
            opponent_elo=args.opponent_elo,
            start_elo=args.start_elo,
        )
        run_benchmark(config)
        return 0

    parser.print_help()
    return 1


def cli_main() -> None:
    raise SystemExit(main())
