from __future__ import annotations

from fastapi import APIRouter, Body, Header, Request as HttpRequest
from fastapi.responses import JSONResponse

from foureyes.core.types import Request

from .deps import bearer_of, parse_meta, resolve_agent

router = APIRouter()


@router.post("/v1/chat/completions")
def chat_completions(http: HttpRequest, body: dict = Body(...), authorization: str | None = Header(None)):
    messages = body.get("messages", [])
    if not isinstance(messages, list):
        return JSONResponse({"error": {"type": "invalid_request", "message": "messages must be a list"}}, status_code=400)
    services = http.app.state.services
    services.policy_store.reload_if_changed()
    agent = resolve_agent(services.policy_store.current(), bearer_of(authorization))
    meta = parse_meta(http.headers, body.get("metadata"))
    req = Request(kind="model", agent_id=agent, session_id=meta["session_id"], channel=meta["channel"],
                  model=body.get("model"), messages=[m for m in messages if isinstance(m, dict)],
                  params={k: body[k] for k in ("max_tokens", "temperature", "tools", "tool_choice") if k in body},
                  meta=meta)
    result = http.app.state.engine.handle_model(req)
    return JSONResponse(result.body, status_code=result.status)
