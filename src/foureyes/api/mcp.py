from __future__ import annotations

import json

from fastapi import APIRouter, Body, Header, Request as HttpRequest
from fastapi.responses import JSONResponse

from foureyes.core.types import Request

from .deps import bearer_of, parse_meta, resolve_agent

router = APIRouter()


def _rpc(id_, result=None, error=None) -> JSONResponse:
    body = {"jsonrpc": "2.0", "id": id_}
    body.update({"error": error} if error else {"result": result})
    return JSONResponse(body)


@router.post("/mcp")
def mcp(http: HttpRequest, body: dict = Body(...), authorization: str | None = Header(None)):
    services, engine = http.app.state.services, http.app.state.engine
    services.policy_store.reload_if_changed()
    agent = resolve_agent(services.policy_store.current(), bearer_of(authorization))
    method, params, rid = body.get("method"), body.get("params") or {}, body.get("id")
    if method == "initialize":
        return _rpc(rid, {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                          "serverInfo": {"name": "foureyes-gateway", "version": "0.1.0"}})
    if method == "tools/list":
        if agent is None:
            return _rpc(rid, error={"code": -32001, "message": "unauthorized"})
        return _rpc(rid, {"tools": engine.list_tools(agent)})
    if method == "tools/call":
        meta = parse_meta(http.headers, params.get("_meta"))
        req = Request(kind="tool", agent_id=agent, session_id=meta["session_id"], channel=meta["channel"],
                      tool=params.get("name"), args=params.get("arguments") or {}, meta=meta)
        res = engine.handle_tool(req)
        payload = res.body if res.status != 200 else {"result": res.body["result"], "foureyes": res.body["foureyes"]}
        return _rpc(rid, {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, default=str)}],
                          "structuredContent": payload, "isError": res.status != 200})
    return _rpc(rid, error={"code": -32601, "message": f"unknown method {method}"})
