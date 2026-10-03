from __future__ import annotations

from urllib.parse import urlparse


def _domain(value: str) -> str:
    v = value.strip().lower()
    if "@" in v:
        return v.rsplit("@", 1)[1].strip(">").strip()
    return urlparse(v if "://" in v else "//" + v).hostname or v


def is_outside(args: dict, tool_cfg: dict) -> bool:
    """True when the recipient is missing/odd or outside allowed_domains (fail-closed)."""
    allowed = [d.lower() for d in tool_cfg.get("allowed_domains", [])]
    value = args.get(tool_cfg.get("egress_arg", "to"))
    for v in value if isinstance(value, list) else [value]:
        if not isinstance(v, str) or not v.strip():
            return True
        d = _domain(v)
        if not any(d == a or d.endswith("." + a) for a in allowed):
            return True
    return False


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
