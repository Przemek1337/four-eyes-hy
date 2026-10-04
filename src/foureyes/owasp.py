from __future__ import annotations

CATEGORIES = [
    ("LLM01:2026", "Prompt Injection"), ("LLM02:2026", "Sensitive Information Disclosure"),
    ("LLM03:2026", "Excessive Agency"), ("LLM04:2026", "Supply Chain"),
    ("LLM05:2026", "Data and Model Poisoning"), ("LLM06:2026", "Unbounded Consumption"),
    ("LLM07:2026", "Misinformation"), ("LLM08:2026", "Hidden Context Exposure"),
    ("LLM09:2026", "Vector and Embedding Weaknesses"), ("LLM10:2026", "Improper Output Handling"),
]

CONTROL_OWASP: dict[str, tuple[str, ...]] = {
    "auth.agent_key": ("LLM03:2026",), "models.allowlist": ("LLM03:2026",), "authz.tools": ("LLM03:2026",),
    "authz.tool_schema": ("LLM03:2026", "LLM05:2026"), "authz.scope": ("LLM09:2026",),
    "data.classify_net": ("LLM02:2026",), "route.model": ("LLM02:2026",),
    "flow.untrusted": ("LLM01:2026", "LLM05:2026"), "dlp.redact_inflight": ("LLM02:2026",),
    "log.redact": ("LLM02:2026",), "output.safe": ("LLM10:2026", "LLM08:2026"),
    "budget.session": ("LLM06:2026",), "budget.spend": ("LLM06:2026",),
    "sig.feed": ("LLM04:2026", "LLM01:2026", "LLM10:2026"),
    "sem.prompt_injection": ("LLM01:2026",), "sem.action_judge": ("LLM01:2026", "LLM03:2026"),
}
ENFORCING = {"enforce", "block", "redact"}
NOTES = {"LLM07:2026": "out of scope: no grounding control in the MVP (documented gap; check.grounding is optional)"}


def coverage(snapshot, blocks: dict[str, int], tested_ids: set[str]) -> dict:
    cats = []
    for cid, name in CATEGORIES:
        tagged = [c for c, tags in CONTROL_OWASP.items() if cid in tags and snapshot.has_control(c)]
        modes = [snapshot.control_cfg(c).get("mode", "enforce") for c in tagged]
        if any(m in ENFORCING for m in modes):
            status = "enforced"
        elif tagged:
            status = "monitor_only"
        else:
            status = "uncovered"
        cats.append({"id": cid, "name": name, "status": status, "controls": tagged,
                     "blocks": blocks.get(cid, 0), "note": NOTES.get(cid, "")})
    tested = len([c for c, _ in CATEGORIES if c in tested_ids])
    return {"edition": "2026", "tested": f"{tested}/10", "categories": cats}
