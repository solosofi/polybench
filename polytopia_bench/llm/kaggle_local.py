from __future__ import annotations

from typing import Any, Optional


class KaggleLocalLLM:
    """Run Kaggle benchmarks LLMs locally (inside Kaggle environment)."""

    def __init__(self, model: Optional[str] = None):
        self.model = model
        self._llm = _resolve_llm(model)

    def generate(self, prompt: str) -> str:
        result = _call_llm(self._llm, prompt)
        if isinstance(result, dict):
            text = result.get("content") or result.get("text")
            if text is not None:
                return str(text).strip()
        if hasattr(result, "content"):
            return str(result.content).strip()
        if hasattr(result, "text"):
            return str(result.text).strip()
        return str(result).strip()


def _resolve_llm(model: Optional[str]) -> Any:
    try:
        from kaggle_benchmarks import kbench
    except Exception as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError(
            "Kaggle local provider requires kaggle_benchmarks. "
            "Run inside a Kaggle notebook or install kaggle_benchmarks."
        ) from exc

    if model:
        if hasattr(kbench, "llms") and isinstance(kbench.llms, dict):
            if model in kbench.llms:
                return kbench.llms[model]
        if hasattr(kbench, "get_llm"):
            try:
                return kbench.get_llm(model)
            except Exception:
                pass
        if hasattr(kbench, "llm"):
            llm = kbench.llm
            if callable(llm):
                try:
                    return llm(model=model)
                except Exception:
                    pass

    if hasattr(kbench, "llm"):
        return kbench.llm
    if hasattr(kbench, "llms") and isinstance(kbench.llms, dict) and kbench.llms:
        return next(iter(kbench.llms.values()))

    raise RuntimeError("No Kaggle LLM available from kaggle_benchmarks.")


def _call_llm(llm: Any, prompt: str) -> Any:
    if hasattr(llm, "generate"):
        return llm.generate(prompt)
    if hasattr(llm, "complete"):
        return llm.complete(prompt)
    if hasattr(llm, "invoke"):
        return llm.invoke(prompt)
    if callable(llm):
        return llm(prompt)
    raise RuntimeError("Unsupported Kaggle LLM interface.")
