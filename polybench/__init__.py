"""Convenience API for MiniRTS Bench."""

from polytopia_bench.benchmark import RunConfig, run_benchmark
from polytopia_bench.game_api import GameAPI, MiniRTSGameAPI


def configure_llm(host=None, model=None, api_key=None, provider="openai"):
    return {
        "llm_provider": provider,
        "llm_host": host,
        "llm_model": model,
        "llm_api_key": api_key,
    }


__all__ = [
    "RunConfig",
    "run_benchmark",
    "configure_llm",
    "GameAPI",
    "MiniRTSGameAPI",
]
