from __future__ import annotations

# Weights are defined in code, not in YAML, so editing the policy cannot change how it is scored.
WEIGHTS = {
    "auth.agent_key": 15, "flow.untrusted": 15, "sem.prompt_injection": 10, "sem.action_judge": 8,
    "authz.tools": 8, "sig.feed": 8, "dlp.redact_inflight": 6, "log.redact": 6, "authz.tool_schema": 5,
    "authz.scope": 5, "data.classify_net": 5, "route.model": 5, "models.allowlist": 4, "output.safe": 4,
    "budget.session": 3, "budget.spend": 3,
}
PENALTY = 10
FORMULA = ("score = 100 − Σ(control weight share: removed = full, monitor = half) "
           "− 10 per weakened part of the provenance wall (max 3) − 10 if the signature feed is stale/failed − 10 per AI decision model that is down − 10 if tests fail")


def compute(snapshot, *, ai_healthy: bool, feed_status: dict, tests: dict | None,
            ai_models_down: tuple[str, ...] | list[str] = ()) -> dict:
    total = sum(WEIGHTS.values())
    score, breakdown = 100.0, []
    for cid, weight in WEIGHTS.items():
        share = weight * 100 / total
        cfg = snapshot.control_cfg(cid)
        if cfg is None:
            deficit, note = share, "removed"
        elif cfg.get("mode") == "monitor":
            deficit, note = share / 2, "monitor only"
        else:
            continue
        score -= deficit
        breakdown.append({"item": cid, "delta": -round(deficit, 1), "note": note})
    for finding in getattr(snapshot, "wall", [])[:3]:
        score -= PENALTY
        breakdown.append({"item": "provenance wall", "delta": -PENALTY, "note": finding})
    if feed_status.get("error") or feed_status.get("version") is None:
        score -= PENALTY
        breakdown.append({"item": "signature feed", "delta": -PENALTY, "note": feed_status.get("error") or "never loaded"})
    if not ai_healthy:
        score -= PENALTY
        breakdown.append({"item": "AI control model", "delta": -PENALTY, "note": "unavailable (fail-closed)"})
    for name in ai_models_down:
        score -= PENALTY
        breakdown.append({"item": f"AI model {name}", "delta": -PENALTY, "note": "unavailable (fail-closed)"})
    if tests and tests.get("failed"):
        score -= PENALTY
        breakdown.append({"item": "test suite", "delta": -PENALTY, "note": f"{tests['failed']} failing"})
    active = sum(1 for cid in WEIGHTS
                 if (cfg := snapshot.control_cfg(cid)) is not None and cfg.get("mode") != "monitor")
    return {"score": max(0, round(score)), "max": 100, "breakdown": breakdown, "formula": FORMULA,
            "controls_active": active, "controls_total": len(WEIGHTS)}
