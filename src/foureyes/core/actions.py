from __future__ import annotations

import re
from urllib.parse import urlparse


_SPLIT = re.compile(r"[\s,;<>()\"']+")
EXTRA_RECIPIENT_ARGS = ("cc", "bcc", "reply_to")


def _domains(value: str) -> list[str]:
    """Every domain a recipient string would reach: all addresses of a list, never just the last one."""
    parts = [p for p in _SPLIT.split(value.strip().lower()) if p]
    if any("@" in p for p in parts):  # words without '@' are display names ("Boss <a@bank.internal>")
        return [p.split("@", 1)[1] for p in parts if "@" in p]  # 'a@x.com@bank.internal' -> 'x.com@bank.internal': never allowed
    return [urlparse(p if "://" in p else "//" + p).hostname or p for p in parts]


def _outside(value, allowed: list[str]) -> bool:
    for v in value if isinstance(value, list) else [value]:
        if not isinstance(v, str) or not v.strip():
            return True
        domains = _domains(v)
        if not domains or any(not any(d == a or d.endswith("." + a) for a in allowed) for d in domains):
            return True
    return False


def is_outside(args: dict, tool_cfg: dict) -> bool:
    """True when any recipient is missing/odd or outside allowed_domains (fail-closed). cc, bcc and reply_to count too."""
    allowed = [d.lower() for d in tool_cfg.get("allowed_domains", [])]
    if _outside(args.get(tool_cfg.get("egress_arg", "to")), allowed):
        return True
    return any(k in args and _outside(args[k], allowed) for k in EXTRA_RECIPIENT_ARGS)


def classify_action(ctx) -> str | None:
    req = ctx.request
    if req.kind != "tool":
        return None
    cfg = ctx.policy.tools.get(req.tool, {})
    tags = cfg.get("tags", [])
    if "egress" in tags and is_outside(req.args, cfg):
        return "egress"
    if "critical" in tags:
        return "critical"
    return None
