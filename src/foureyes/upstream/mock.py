from __future__ import annotations

from typing import Any, Callable

from .base import ModelResponse, UpstreamError

Script = Callable[[str, list[dict], list[dict] | None], dict]


class MockModelUpstream:
    """Deterministic model: fixed usage and time so budgets are reproducible in tests."""

    def __init__(self, type: str, script: Script | None = None, seconds: float = 0.05,
                 usage: tuple[int, int] = (100, 50)):
        self.type = type
        self.script = script
        self.seconds = seconds
        self.usage = usage
        self.available = True
        self.calls: list[dict] = []

    def chat(self, model: str, messages: list[dict], tools: list[dict] | None = None, **params: Any) -> ModelResponse:
        if not self.available:
            raise UpstreamError(f"{self.type} upstream unavailable")
        self.calls.append({"model": model, "messages": messages, "params": params})
        message = self.script(model, messages, tools) if self.script else {"role": "assistant", "content": "mock reply"}
        p, c = self.usage
        return ModelResponse(message=message, usage={"prompt_tokens": p, "completion_tokens": c,
                                                     "total_tokens": p + c},
                             seconds=self.seconds, model=model)
