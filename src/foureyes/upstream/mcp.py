from __future__ import annotations

import json

import httpx

from .base import UpstreamError


class McpUpstream:
    """Minimal MCP-compatible client: JSON-RPC 2.0 over HTTP (tools/list, tools/call)."""

    def __init__(self, url: str, client: httpx.Client | None = None):
        self.url = url
        self.client = client or httpx.Client(timeout=60.0)
        self._id = 0

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        try:
            resp = self.client.post(self.url, json={"jsonrpc": "2.0", "id": self._id,
                                                    "method": method, "params": params or {}})
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UpstreamError(f"tool server failed: {exc}") from exc
        if "error" in body:
            raise UpstreamError(f"tool server error: {body['error']}")
        return body["result"]

    def list_tools(self) -> list[dict]:
        return self._rpc("tools/list")["tools"]

    def call(self, name: str, arguments: dict) -> dict:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        text = " ".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        if result.get("isError"):
            raise UpstreamError(f"tool {name} failed: {text}")
        if "structuredContent" in result:
            return result["structuredContent"]
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except ValueError:
            return {"text": text}
