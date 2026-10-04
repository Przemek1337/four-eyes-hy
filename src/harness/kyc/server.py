from __future__ import annotations

import json

from fastapi import Body, FastAPI

from .tools import KycTools


def create_tool_app(tools: KycTools) -> FastAPI:
    """A tiny MCP-compatible tool server (JSON-RPC over HTTP). It sits behind the gateway."""
    app = FastAPI(title="KYC tools")
    handlers, schemas = tools.handlers(), tools.schemas()

    @app.post("/mcp")
    def mcp(body: dict = Body(...)):
        rid, method, params = body.get("id"), body.get("method"), body.get("params") or {}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": rid, "result": {"tools": [
                {"name": n, "description": n.replace("_", " "), "inputSchema": schemas[n]} for n in handlers]}}
        if method == "tools/call":
            name, args = params.get("name"), params.get("arguments") or {}
            if name not in handlers:
                return {"jsonrpc": "2.0", "id": rid, "result": {"isError": True, "content": [{"type": "text", "text": f"unknown tool {name}"}]}}
            try:
                out = handlers[name](**args)
            except TypeError as exc:
                return {"jsonrpc": "2.0", "id": rid, "result": {"isError": True, "content": [{"type": "text", "text": str(exc)}]}}
            return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": json.dumps(out)}],
                                                             "structuredContent": out, "isError": False}}
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "unknown method"}}

    return app
