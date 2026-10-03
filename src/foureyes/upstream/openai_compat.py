from __future__ import annotations

import time
from typing import Any

import httpx

from .base import ModelResponse, UpstreamError


class OpenAICompatUpstream:
    """Any OpenAI-compatible server (Ollama, vLLM, ...)."""

    def __init__(self, base_url: str, type: str, client: httpx.Client | None = None,
                 api_key: str | None = None, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.type = type
        self.client = client or httpx.Client(timeout=timeout)
        self.api_key = api_key

    def chat(self, model: str, messages: list[dict], tools: list[dict] | None = None, **params: Any) -> ModelResponse:
        payload: dict[str, Any] = {"model": model, "messages": messages, **params}
        if tools:
            payload["tools"] = tools
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        t0 = time.perf_counter()
        try:
            resp = self.client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            message = data["choices"][0]["message"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise UpstreamError(f"{self.type} upstream failed: {exc}") from exc
        return ModelResponse(message=message, usage=data.get("usage", {}),
                             seconds=time.perf_counter() - t0, model=model)
