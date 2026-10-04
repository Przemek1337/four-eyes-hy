from __future__ import annotations

import hmac
import os
import uuid


def bearer_of(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def resolve_agent(snapshot, bearer: str | None) -> str | None:
    if not bearer:
        return None
    for agent_id, cfg in snapshot.agents.items():
        key = os.environ.get(cfg.get("key_ref", ""))
        if key and hmac.compare_digest(key, bearer):
            return agent_id
    return None


def parse_meta(headers, body_meta: dict | None) -> dict:
    meta = dict(body_meta or {})
    h = headers.get
    if h("x-foureyes-session"):
        meta["session_id"] = h("x-foureyes-session")
    if h("x-foureyes-channel"):
        meta["channel"] = h("x-foureyes-channel")
    if h("x-foureyes-task"):
        meta["task"] = h("x-foureyes-task")
    if h("x-foureyes-approval"):
        meta["approval_id"] = h("x-foureyes-approval")
    if h("x-foureyes-scope"):
        meta["scope"] = dict(p.split("=", 1) for p in h("x-foureyes-scope").split(",") if "=" in p)
    if h("x-foureyes-terms"):
        meta["sensitive_terms"] = [t.strip() for t in h("x-foureyes-terms").split(",") if t.strip()]
    meta.setdefault("session_id", uuid.uuid4().hex[:12])
    meta.setdefault("channel", "chat")
    if not isinstance(meta.get("scope", {}), dict):
        meta["scope"] = {}
    return meta
