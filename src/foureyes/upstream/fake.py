from __future__ import annotations

from typing import Callable

from .base import UpstreamError


class FakeToolUpstream:
    def __init__(self, handlers: dict[str, Callable[..., dict]], schemas: dict[str, dict] | None = None):
        self.handlers = handlers
        self.schemas = schemas or {}

    def list_tools(self) -> list[dict]:
        return [{"name": n, "description": n, "inputSchema": self.schemas.get(n, {"type": "object"})}
                for n in self.handlers]

    def call(self, name: str, arguments: dict) -> dict:
        if name not in self.handlers:
            raise UpstreamError(f"unknown tool {name}")
        return self.handlers[name](**arguments)
