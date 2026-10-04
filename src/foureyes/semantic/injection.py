from __future__ import annotations

from typing import Protocol


class InjectionScorer(Protocol):
    def score(self, text: str) -> float: ...

    def healthy(self) -> bool: ...


class MockInjectionScorer:
    """Deterministic stand-in for a prompt-injection classifier (used in tests and offline demos)."""
    PATTERNS = ("ignore previous instructions", "ignore all previous", "disregard", "you are now",
                "reveal your system prompt", "print your instructions", "ignoruj poprzednie")

    def __init__(self, fixed: float | None = None, fail: bool = False, extra_patterns: tuple[str, ...] = ()):
        self.fixed = fixed
        self.fail = fail
        self.patterns = self.PATTERNS + tuple(p.lower() for p in extra_patterns)  # domain phrases come from the caller

    def score(self, text: str) -> float:
        if self.fail:
            raise RuntimeError("injection scorer unavailable")
        if self.fixed is not None:
            return self.fixed
        lowered = text.lower()
        return 0.95 if any(p in lowered for p in self.patterns) else 0.03

    def healthy(self) -> bool:
        return not self.fail


class HFInjectionScorer:
    """Real classifier through transformers (`pip install -e '.[ml]'`). Model id is configurable:
    Llama Prompt Guard 2 is license-gated; protectai/deberta-v3-base-prompt-injection-v2 is an open alternative."""

    def __init__(self, model_id: str = "protectai/deberta-v3-base-prompt-injection-v2"):
        from transformers import pipeline  # lazy: keeps the core importable without the ml extra

        self._pipe = pipeline("text-classification", model=model_id, truncation=True, max_length=512)

    def score(self, text: str) -> float:
        out = self._pipe(text[:4000])[0]
        label = str(out["label"]).upper()
        return float(out["score"]) if "INJECTION" in label or label in ("LABEL_1", "MALICIOUS", "JAILBREAK") \
            else 1.0 - float(out["score"])

    def healthy(self) -> bool:
        return True
