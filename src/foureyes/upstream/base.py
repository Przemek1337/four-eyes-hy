from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class UpstreamError(Exception):
    pass


@dataclass
class ModelResponse:
    message: dict
    usage: dict
    seconds: float
    model: str  # the name the gateway asked for
    served_model: str | None = None  # the name the server says answered, when it says; None means unknown


class ModelUpstream(Protocol):
    type: str

    def chat(self, model: str, messages: list[dict], tools: list[dict] | None = None, **params: Any) -> ModelResponse: ...


class ToolUpstream(Protocol):
    def list_tools(self) -> list[dict]: ...

    def call(self, name: str, arguments: dict) -> dict: ...


@dataclass
class UpstreamRegistry:
    models: dict[str, ModelUpstream] = field(default_factory=dict)  # provider name -> upstream
    tools: ToolUpstream | None = None
