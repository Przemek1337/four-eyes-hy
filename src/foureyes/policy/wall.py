from __future__ import annotations

"""Checks of the provenance wall. The wall is not one control: it is the sources that label content untrusted, the
tools tagged egress or critical, and the label rules that act on both. Weakening any of them leaves every control
enabled and the posture at 100, so it is checked here, not in the control catalog."""


def wall_findings(policy) -> list[str]:
    out: list[str] = []
    sources = [v for k, v in policy.sources.items() if k != "default_class" and isinstance(v, dict)]
    if not any("untrusted" in v.get("labels", []) for v in sources):
        out.append("no data source is labelled untrusted: no session can ever become untrusted")
    rules = {r.get("when", {}).get("session"): r for r in policy.labels.get("rules", []) if isinstance(r, dict)}
    for session in ("untrusted", "high_risk"):
        rule = rules.get(session)
        if rule is None:
            out.append(f"no label rule for {session} sessions: their egress and critical actions are not gated")
        elif rule.get("egress") not in ("APPROVAL", "BLOCK"):
            out.append(f"{session} sessions may send data out without a human (labels.rules egress)")
    if not any("egress" in t.get("tags", []) for t in policy.tools.values()):
        out.append("no tool is tagged egress: nothing counts as data leaving the bank")
    for name, tool in policy.tools.items():
        for domain in tool.get("allowed_domains", []):
            if "*" in str(domain) or "." not in str(domain):
                out.append(f"tools.{name}.allowed_domains: {domain!r} is too broad to be a bank domain")
    for kind, cfg in policy.dlp.items():
        if isinstance(cfg, dict) and cfg.get("on_detect") == "monitor":
            out.append(f"dlp.{kind} only monitors: nothing is redacted or blocked")
    return out
