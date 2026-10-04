from __future__ import annotations

import base64
import binascii
import json
import os
import queue
import statistics
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Query, Request as HttpRequest
from fastapi.responses import JSONResponse, StreamingResponse

from foureyes.core.telemetry import percentile
from foureyes.core.types import Request
from foureyes.owasp import CONTROL_OWASP, coverage
from foureyes.policy.catalog import CATALOG_IDS
from foureyes.posture import WEIGHTS, compute
from foureyes.semantic.decision_model_types import LEGACY_MODELS, model_refs
from foureyes.signatures.feed import KNOWN_TYPES

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # Playground document mode: a client PDF, at most 5 MB

INFO = {
    "auth.agent_key": ("Without a valid agent key nothing runs; identity comes from the key.", "det"),
    "models.allowlist": ("Only models listed in the policy can be requested.", "det"),
    "authz.tools": ("An agent uses only its own tools, in the required order.", "det"),
    "authz.tool_schema": ("Tool arguments must match the tool's schema; limits can escalate to a human.", "det"),
    "authz.scope": ("An agent sees only the case it works on; search results are filtered to that scope.", "det"),
    "data.classify_net": ("Detects personal data in unlabeled input and raises the session's data class.", "det"),
    "route.model": ("Chooses local or external upstream within what the data class allows.", "det"),
    "flow.untrusted": ("After reading untrusted content, data cannot leave the bank or be approved without a human.", "det"),
    "dlp.redact_inflight": ("Redacts secrets, removes unneeded fields and masks PII headed outside the bank.", "det"),
    "log.redact": ("Redacts sensitive values in audit logs, exports and dashboards.", "det"),
    "output.safe": ("Strips foreign links, images and scripts from answers and detects system-prompt leaks.", "det"),
    "budget.session": ("Caps tokens and steps per session to stop runaway loops.", "det"),
    "budget.spend": ("Daily USD / compute-second limits per agent and monthly per team; block, fall back to local or ask a human.", "det"),
    "sig.feed": ("Blocks known attacks from an external signature feed.", "det"),
    "sem.prompt_injection": ("A classifier scores prompts and documents for prompt injection.", "ai"),
    "sem.action_judge": ("A local model checks that a critical action's real parameters fit the case task.", "ai"),
}
EMPTY_REPORT = {"passed": 0, "failed": 0, "positive": {"passed": 0, "failed": 0},
                "negative": {"passed": 0, "failed": 0}, "by_owasp": {}, "false_blocks": 0, "missed_attacks": 0,
                "ran_at": None, "policy_version": None}
DECISIONS = ("ALLOW", "REDACT", "APPROVAL", "BLOCK")
MAX_QUESTION_CHARS = 2000
HISTORY_CHARS = 4000  # Playground keeps the last exchange only, each side cut to this length
REPORT = Path(os.environ.get("FOUREYES_REPORT", "reports/test_report.json"))


def _services(http: HttpRequest):
    return http.app.state.services


def _decisions(services) -> list[dict]:
    return services.audit.events(event="decision")


def _read_report() -> dict | None:
    try:
        return json.loads(REPORT.read_text())
    except (OSError, ValueError):
        return None


def sse_line(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"


def _session_row(services, s, decisions: list[dict]) -> dict:
    mine = [e for e in decisions if e["session_id"] == s.session_id]
    status = "high_risk" if "high_risk" in s.labels else "untrusted" if "untrusted" in s.labels else "clean"
    return {"session_id": s.session_id, "agent": s.agent_id, "client": next(iter(s.scope.values()), None),
            "started": s.created, "steps": s.steps,
            "labels": sorted(s.labels), "data_class": s.data_class, "status": status,
            "last_decision": mine[-1]["decision"] if mine else None,
            "blocked_count": sum(1 for e in mine if e["decision"] == "BLOCK"),
            "pending_approvals": sum(1 for a in services.approvals.pending() if a.session_id == s.session_id)}


FLOW_OUTCOME = {"ALLOW": "passed", "REDACT": "passed", "BLOCK": "blocked", "APPROVAL": "held"}


def _flow(services, sess, events: list[dict]) -> dict:
    """Where the session's data came from and where it went, derived only from its audit events."""
    snap = services.policy_store.current()
    decs = [e for e in events if e.get("event", "decision") == "decision"]
    first_model = next((e for e in decs if e.get("kind") == "model"), None)
    sources = []
    if sess.task or first_model:
        sources.append({"name": "User request", "detail": sess.task or (first_model.get("content") or "")[:80],
                        "label": "trusted"})
    for e in decs:
        entry = snap.policy.sources.get(f"mcp:{e.get('resource')}")
        if e.get("kind") == "tool" and e["decision"] in ("ALLOW", "REDACT") and isinstance(entry, dict) \
                and not any(x["name"] == e["resource"] for x in sources):
            sources.append({"name": e["resource"], "detail": f"{entry['class']} data",
                            "label": "untrusted" if "untrusted" in entry.get("labels", []) else entry["class"]})
    model_ev = [e for e in decs if e.get("kind") == "model" and e.get("route")]
    last_model = model_ev[-1]["route"] if model_ev else None
    lowest = snap.class_order[0]
    first_labeled = next((i for i, e in enumerate(decs, 1) if e.get("labels")), None)
    agent = {"name": sess.agent_id, "model": f"{last_model.get('served_model') or last_model['model']} ({last_model['chosen']})" if last_model else "",
             "labels": sorted(sess.labels) + ([sess.data_class] if sess.data_class != lowest else []),
             "labels_since_step": first_labeled}
    allowed = snap.allowed_upstream_types(sess.data_class)
    destinations = []
    for ptype in ("local", "external"):
        used = [FLOW_OUTCOME[e["decision"]] for e in model_ev if e["route"]["chosen"] == ptype]
        name = f"{ptype.capitalize()} model"
        if ptype not in allowed:
            destinations.append({"name": name, "detail": f"Not allowed for {sess.data_class}", "outcome": "unavailable"})
        elif used:
            destinations.append({"name": name, "detail": f"Allowed for {sess.data_class}",
                                 "outcome": "passed" if "passed" in used else used[-1]})
    last_by_tool: dict[str, dict] = {}
    for e in decs:
        if e.get("kind") == "tool" and {"egress", "critical"} & set(snap.tools.get(e["resource"], {}).get("tags", [])):
            last_by_tool[e["resource"]] = e
    for tool, e in last_by_tool.items():
        arg = snap.tools[tool].get("egress_arg")
        try:
            detail = str(json.loads(e.get("content") or "{}").get(arg)) if arg else ""
        except (ValueError, AttributeError):
            detail = ""
        destinations.append({"name": tool, "detail": detail if detail not in ("", "None") else e.get("reason", ""),
                             "outcome": FLOW_OUTCOME[e["decision"]]})
    return {"sources": sources, "agent": agent, "destinations": destinations}


def _decision_model_latency(decisions: list[dict]) -> dict[str, dict]:
    """p50/p95 latency per decision model (spec 4.5), from the `ai` blocks the AI controls wrote to the audit."""
    by_model: dict[str, list[float]] = {}
    for e in decisions:
        for assessment in (e.get("ai") or {}).values():
            if isinstance(assessment, dict) and assessment.get("model") and assessment.get("latency_ms") is not None:
                by_model.setdefault(assessment["model"], []).append(float(assessment["latency_ms"]))
    return {name: {"p50_ms": percentile(ms, 50), "p95_ms": percentile(ms, 95), "n": len(ms)}
            for name, ms in sorted(by_model.items())}


@router.get("/metrics")
def metrics(http: HttpRequest):
    s = _services(http)
    snap = s.policy_store.current()
    lowest = snap.class_order[0]
    decisions = _decisions(s)
    by_decision = {d: sum(1 for e in decisions if e["decision"] == d) for d in DECISIONS}
    by_class: dict[str, int] = {}
    by_upstream = {"local": 0, "external": 0}
    private_to_external = 0
    cost = {"local_usd": 0.0, "external_usd": 0.0, "compute_s": 0.0}
    now = time.time()
    routing = {c: {"data_class": c, "local": 0, "external": 0} for c in snap.class_order}
    blockers: dict[str, dict] = {}
    redacted_fields = 0
    for e in decisions:
        by_class[e["data_class"]] = by_class.get(e["data_class"], 0) + 1
        up = e.get("upstream_type")
        if e["decision"] == "BLOCK":
            b = blockers.setdefault(e["rule"], {"rule": e["rule"], "owasp": [], "blocked": 0})
            b["blocked"] += 1
            b["owasp"] += [t for t in e.get("owasp") or [] if t not in b["owasp"]]
        if e["decision"] == "REDACT" and e["rule"] == "dlp.redact_inflight":
            removed = (e.get("detail") or {}).get("removed")
            redacted_fields += removed if isinstance(removed, int) else 1
        if up and e["decision"] in ("ALLOW", "REDACT") and e.get("kind") == "model":
            by_upstream[up] += 1
            routing.setdefault(e["data_class"], {"data_class": e["data_class"], "local": 0, "external": 0})[up] += 1
            if up == "external" and e["data_class"] != lowest:
                private_to_external += 1
        key = "external_usd" if up == "external" else "local_usd"
        cost[key] += e.get("cost_usd") or 0.0
        cost["compute_s"] += e.get("compute_s") or 0.0
    latency = s.telemetry.snapshot()
    latency["upstream_p95_ms"] = latency["upstream"]["p95"]
    decided = [a.decided_at - a.created for a in s.approvals.all() if a.decided_at is not None]
    return {"requests": len(decisions), "by_decision": by_decision, "open_approvals": len(s.approvals.pending()),
            "by_class": by_class, "by_upstream_type": by_upstream, "private_to_external": private_to_external,
            "policy_version": snap.label, "latency": latency, "cost": cost,
            "feed": s.feed.status(),
            "throughput_per_min": sum(1 for e in decisions if (e.get("ts_epoch") or 0) >= now - 60),
            "top_blockers": sorted(blockers.values(), key=lambda b: -b["blocked"])[:10],
            "routing": list(routing.values()), "redacted_fields": redacted_fields,
            "decision_models": _decision_model_latency(decisions),
            "approval_median_s": statistics.median(decided) if decided else None,
            "approvals_expired": sum(1 for a in s.approvals.all()
                                     if a.status == "pending" and a.expires_at <= s.approvals.clock())}


@router.get("/admin/sessions")
def sessions(http: HttpRequest, agent: str | None = None, decision: str | None = None,
             data_class: str | None = None, rule: str | None = None):
    s = _services(http)
    decisions = _decisions(s)
    rows = []
    for sess in s.sessions.all():
        if agent and sess.agent_id != agent:
            continue
        if data_class and sess.data_class != data_class:
            continue
        mine = [e for e in decisions if e["session_id"] == sess.session_id]
        if decision and not any(e["decision"] == decision for e in mine):
            continue
        if rule and not any(e["rule"] == rule for e in mine):
            continue
        rows.append(_session_row(s, sess, decisions))
    return {"sessions": sorted(rows, key=lambda r: r["started"], reverse=True)}


@router.get("/admin/sessions/{session_id}")
def session_detail(http: HttpRequest, session_id: str):
    s = _services(http)
    sess = s.sessions.get(session_id)
    if sess is None:
        raise HTTPException(404, "unknown session")
    events = [{"latency_ms": None, "route": None, **e} for e in s.audit.events(session=session_id)
              if e.get("event", "decision") in ("decision", "class.raised", "label.added")]
    row = _session_row(s, sess, _decisions(s))
    row.update(scope=sess.scope, task=sess.task)
    return {"session": row, "events": events,
            "approvals": [a.to_dict() for a in s.approvals.all() if a.session_id == session_id],
            "flow": _flow(s, sess, events)}


@router.get("/admin/approvals")
def approvals(http: HttpRequest, status: str = Query("pending", pattern="^(pending|all)$")):
    svc = _services(http).approvals
    return {"approvals": [a.to_dict() for a in (svc.pending() if status == "pending" else svc.all())]}


@router.post("/admin/approvals/{approval_id}/decide")
def decide(http: HttpRequest, approval_id: str, body: dict = Body(...)):
    svc = _services(http).approvals
    if svc.get(approval_id) is None:
        raise HTTPException(404, "unknown approval")
    a = svc.decide(approval_id, bool(body.get("approve")), by=body.get("by", "compliance"))
    _services(http).audit.emit({"event": "approval.decided", "approval_id": a.id, "session_id": a.session_id,
                                "agent": a.agent_id, "tool": a.tool, "status": a.status, "by": a.decided_by})
    return a.to_dict()


def _setting(cid: str, cfg: dict | None) -> str:
    if cfg is None:
        return "removed"
    if cfg.get("mode") == "monitor":
        return "monitor"
    if cid == "sem.prompt_injection":
        return f"block above {cfg.get('prompts', {}).get('block_above', 0.8)}"
    if cid == "sem.action_judge":
        return f"escalate above {cfg.get('escalate_above', 0.7)}"
    return cfg.get("mode", "enforce")


@router.get("/admin/controls")
def controls(http: HttpRequest):
    s = _services(http)
    snap = s.policy_store.current()
    tele = s.telemetry.snapshot()["controls"]
    cutoff = time.time() - 3600
    hits: dict[str, int] = {}
    for e in _decisions(s):
        if e["decision"] != "ALLOW" and (e.get("ts_epoch") or cutoff) >= cutoff:
            hits[e["rule"]] = hits.get(e["rule"], 0) + 1
    refs = model_refs(snap.controls)
    health = s.decision_models.health(snap) if s.decision_models else {}
    rows = []
    for cid in CATALOG_IDS:
        cfg = snap.control_cfg(cid)
        desc, kind = INFO[cid]
        status = "REMOVED" if cfg is None else "monitor" if cfg.get("mode") == "monitor" else "active"
        rows.append({"id": cid, "description": desc, "type": kind, "status": status, "setting": _setting(cid, cfg),
                     "mode": (cfg or {}).get("mode", "enforce" if cfg is not None else None),
                     "params": {k: v for k, v in (cfg or {}).items() if k != "mode"},
                     "owasp": list(CONTROL_OWASP.get(cid, ())), "hits_1h": hits.get(cid, 0),
                     "p95_ms": tele.get(cid, {}).get("p95", 0.0), "weight": WEIGHTS.get(cid, 0),
                     "model": refs.get(cid),
                     "model_status": (None if refs.get(cid) not in health
                                      else "up" if health[refs.get(cid)] else "down")})
    reloads = [h for h in s.policy_store.history if h["event"] == "policy.reloaded"]
    return {"controls": rows, "last_diff": reloads[-1]["diff"] if reloads else []}


def _uses_legacy(snap, cid: str, registry) -> bool:
    name = model_refs(snap.controls).get(cid)
    return snap.has_control(cid) and (registry is None or name is None or name in LEGACY_MODELS.get(cid, ()))


def _posture(s) -> dict:
    snap = s.policy_store.current()
    registry = s.decision_models
    ai_ok = True
    if _uses_legacy(snap, "sem.prompt_injection", registry):
        ai_ok &= bool(s.injection.healthy())
    if _uses_legacy(snap, "sem.action_judge", registry):
        ai_ok &= bool(s.judge.healthy())
    down = [n for n, ok in (registry.health(snap) if registry else {}).items() if not ok]
    return compute(snap, ai_healthy=ai_ok, feed_status=s.feed.status(), tests=_read_report(), ai_models_down=down)


@router.get("/admin/posture")
def posture(http: HttpRequest):
    return _posture(_services(http))


@router.get("/admin/owasp")
def owasp(http: HttpRequest):
    s = _services(http)
    blocks: dict[str, int] = {}
    for e in _decisions(s):
        if e["decision"] == "BLOCK":
            for tag in e.get("owasp") or []:
                blocks[tag] = blocks.get(tag, 0) + 1
    report = _read_report() or {}
    tested = {k for k, v in (report.get("by_owasp") or {}).items() if v.get("passed", 0) > 0}
    return coverage(s.policy_store.current(), blocks, tested)


def _summary(snap) -> dict:
    inj, out, logs = (snap.control_cfg(c) for c in ("sem.prompt_injection", "output.safe", "log.redact"))
    dlp_on = snap.has_control("dlp.redact_inflight")
    guard = []
    if inj is not None:
        p = inj.get("prompts", {})
        guard.append({"label": "Prompt injection", "value": "monitor only" if inj.get("mode") == "monitor" else
                      f"block above {p.get('block_above', 0.8)}, log above {p.get('log_above', 0.5)}"})
        guard.append({"label": "Client documents",
                      "value": f"flag above {inj.get('documents', {}).get('flag_above', 0.5)}, no block"})
    for kind, label in (("secrets", "Secrets"), ("pii_in_prompt", "Personal data in prompts"),
                        ("field_minimization", "Unneeded fields"), ("egress_sinks", "Egress sinks")):
        action = snap.dlp_value(kind, "on_detect")
        if action:
            guard.append({"label": label, "value": str(action).replace("_", " ") if dlp_on else "off"})
    guard.append({"label": "Model output", "value": "off" if out is None else
                  f"{out.get('mode', 'enforce')}, allowed domains {', '.join(out.get('allowed_domains', [])) or 'none'}"})
    guard.append({"label": "Logs", "value": "off" if logs is None else logs.get("mode", "enforce")})
    models = []
    for name, entry in snap.models().items():
        ptype = snap.provider_type(entry["provider"])
        classes = [c for c in snap.class_order if ptype in snap.allowed_upstream_types(c)]
        value = ("all data classes" if len(classes) == len(snap.class_order) else
                 f"{', '.join(classes)} data only" if classes else "no data classes")
        models.append({"label": f"{ptype.capitalize()} · {name}", "value": value})
    if inj is not None:
        models.append({"label": "AI checks", "value": "fail closed on error" if inj.get("on_error", "fail_closed")
                       == "fail_closed" else "fail open on error"})
    b = snap.budgets
    budgets = []
    for agent, lim in (b.get("agents") or {}).items():
        parts = ([f"${lim['daily_usd']:.2f}"] if lim.get("daily_usd") else []) + \
                ([f"{lim['daily_compute_seconds']:g} compute s"] if lim.get("daily_compute_seconds") else [])
        if parts:
            budgets.append({"label": agent, "value": " and ".join(parts) + " a day"})
    for team, lim in (b.get("teams") or {}).items():
        if lim.get("monthly_usd"):
            budgets.append({"label": f"Team {team}", "value": f"${lim['monthly_usd']:.2f} a month"})
    sess = b.get("session") or {}
    if sess:
        budgets.append({"label": "Session", "value": ", ".join(
            x for x in (f"{sess['max_tokens']:,} tokens" if sess.get("max_tokens") else "",
                        f"{sess['max_steps']} steps" if sess.get("max_steps") else "") if x)})
    budgets.append({"label": f"Alert at {b.get('soft_limit_pct', 80)}%, when over", "value": b.get("on_exceeded", "block")})
    return {"block_or_redact": guard, "models": models, "budgets": budgets}


@router.get("/admin/signatures")
def signatures(http: HttpRequest):
    s = _services(http)
    blocked: dict[str, int] = {}
    for e in _decisions(s):
        if e["decision"] == "BLOCK" and e.get("signature_id"):
            blocked[e["signature_id"]] = blocked.get(e["signature_id"], 0) + 1
    hits = []
    for kind in sorted(KNOWN_TYPES):
        for sig in s.feed.by_type(kind):
            pats = sig.get("match") or sig.get("allowed_sources") or []
            matches = (", ".join(map(str, pats[:3])) + (" ..." if len(pats) > 3 else "")) if pats \
                else kind.replace("_", " ")
            hits.append({"type": kind, "matches": matches, "reference": sig.get("reference"),
                         "signature_id": sig["id"], "blocked": blocked.get(sig["id"], 0)})
    return {"feed": s.feed.status(), "hits": hits}


@router.get("/admin/timeseries")
def timeseries(http: HttpRequest, window: str = Query("24h", pattern=r"^[1-9]\d{0,2}h$")):
    hours, step = int(window[:-1]), 3600
    end = int(time.time() // step * step)
    buckets = {end - i * step: {"ts": end - i * step, "requests": 0, "blocked": 0, "approval": 0, "redact": 0, "_g": []}
               for i in range(hours - 1, -1, -1)}
    for e in _decisions(_services(http)):
        b = buckets.get(int((e.get("ts_epoch") or 0) // step * step))
        if b is None:
            continue
        b["requests"] += 1
        for key, outcome in (("blocked", "BLOCK"), ("approval", "APPROVAL"), ("redact", "REDACT")):
            b[key] += e["decision"] == outcome
        if e.get("gateway_ms") is not None:
            b["_g"].append(e["gateway_ms"])
    points = [{**{k: v for k, v in b.items() if k != "_g"},
               "gateway_p95_ms": percentile(b["_g"], 95) if b["_g"] else None} for b in buckets.values()]
    return {"bucket_s": step, "points": points}


@router.get("/admin/policy")
def policy(http: HttpRequest):
    s = _services(http)
    snap = s.policy_store.current()
    return {"version": snap.label, "profile": snap.policy.profile, "error": s.policy_store.last_error,
            "history": list(reversed(s.policy_store.history[-20:])), "feed": s.feed.status(),
            "summary": _summary(snap)}


@router.get("/admin/budgets")
def budgets(http: HttpRequest):
    s = _services(http)
    snap = s.policy_store.current()
    out = s.meter.usage_summary(snap)
    now = time.time()
    per_agent: dict[str, float] = {}
    per_team: dict[str, float] = {}
    for e in _decisions(s):
        if e.get("upstream_type") == "external" and (e.get("ts_epoch") or 0) >= now - 3600:
            per_agent[e["agent"]] = per_agent.get(e["agent"], 0.0) + (e.get("cost_usd") or 0.0)
            team = snap.team_of(e["agent"])
            if team:
                per_team[team] = per_team.get(team, 0.0) + (e.get("cost_usd") or 0.0)

    def rate(row: dict, last_hour: float) -> None:
        row["usd_per_hour"] = last_hour
        limit = row["usd_limit"]
        row["projected_exhaust_at"] = (now + max(0.0, limit - row["usd_used"]) / last_hour * 3600
                                       if limit and last_hour > 0 else None)

    for a in out["agents"]:
        a["tokens_used"] = s.meter.agent_daily(a["agent"], "tokens")
        rate(a, per_agent.get(a["agent"], 0.0))
    for t in out["teams"]:
        rate(t, per_team.get(t["team"], 0.0))
    sess = snap.budgets.get("session") or {}
    live = s.sessions.all()
    out["session_limits"] = {"max_tokens": sess.get("max_tokens"), "max_steps": sess.get("max_steps"),
                             "busiest": {"tokens": max((x.tokens for x in live), default=0),
                                         "steps": max((x.steps for x in live), default=0)},
                             "stopped_by_limit": sum(1 for e in _decisions(s)
                                                     if (e.get("code") or "").startswith("SESSION_"))}
    return out


@router.get("/admin/tests")
def tests_report():
    return {**EMPTY_REPORT, **(_read_report() or {})}


@router.post("/admin/chat")
def chat(http: HttpRequest, body: dict = Body(...)):
    s, engine = _services(http), http.app.state.engine
    mode = body.get("mode")
    if mode not in ("prompt", "document"):
        raise HTTPException(400, "mode must be prompt or document")
    text = str(body.get("text", ""))
    sid = body.get("session_id") or f"chat-{uuid.uuid4().hex[:8]}"
    if mode == "document":
        if s.document_runner is None:
            return JSONResponse({"error": "no harness runner is configured for document mode"}, status_code=501)
        question = body.get("question")  # asked next to the file; optional, goes to the agent as a prompt, not as document text
        if question is not None and not isinstance(question, str):
            raise HTTPException(400, "question must be a string")
        asked = {"question": question.strip()} if question and question.strip() else {}
        if len(asked.get("question", "")) > MAX_QUESTION_CHARS:
            raise HTTPException(400, f"question is longer than {MAX_QUESTION_CHARS} characters")
        upload = body.get("file")
        if upload is None:
            return s.document_runner(text=text, session_id=sid, **asked)
        if not isinstance(upload, dict):
            raise HTTPException(400, "file must be an object with name, content_type and content_base64")
        try:
            pdf = base64.b64decode(str(upload.get("content_base64", "")), validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(400, "file.content_base64 is not valid base64")
        if len(pdf) > MAX_UPLOAD_BYTES:
            return JSONResponse({"error": {"message": "the file is larger than 5 MB"}}, status_code=413)
        try:
            return s.document_runner(text=text, session_id=sid, pdf=pdf, **asked)
        except ValueError as exc:  # the harness could not read it: not a PDF, encrypted, no text layer
            return JSONResponse({"error": {"message": str(exc)}}, status_code=422)
    agent = s.chat_agent or "playground-agent"
    # The model sees the previous exchange. The gateway keeps it itself, from what it delivered, instead of taking a
    # history from the browser: a forged "assistant" message would not be read as text to check.
    earlier = s.sessions.get(sid)
    history = list(earlier.last_turn) if earlier else []
    req = Request(kind="model", agent_id=agent, session_id=sid, channel="chat", model=body.get("model") or "auto",
                  messages=history + [{"role": "user", "content": text}], meta={"session_id": sid, "channel": "chat"})
    res = engine.handle_model(req)
    if res.status == 200:
        reply_text = res.body["choices"][0]["message"].get("content")
        kept = s.sessions.get(sid)
        if kept is not None and isinstance(reply_text, str):  # the user's text after any redaction, and the reply as delivered
            kept.last_turn = [{"role": "user", "content": str(req.messages[-1].get("content", ""))[:HISTORY_CHARS]},
                              {"role": "assistant", "content": reply_text[:HISTORY_CHARS]}]
    ev = next((e for e in reversed(s.audit.events(session=sid)) if e.get("decision_id") == res.decision_id), {})
    v = res.verdict
    ok = res.status == 200
    r = ev.get("route")
    route = ({"type": r["chosen"], "model": r["model"], "served_model": r.get("served_model"), "router": r["router"],
              "rerouted_from": r["rerouted_from"]}
             if r else None)
    return {"session_id": sid, "decision": res.outcome.value, "rule": v.rule if v else None,
            "layer": v.layer if v else None, "code": v.code if v else None,
            "owasp": list(v.owasp) if v else [], "data_class": ev.get("data_class"),
            "route": route, "latency_ms": ev.get("latency_ms"),
            "injection_score": ev.get("injection_score"), "ai": ev.get("ai"),
            "reply": res.body["choices"][0]["message"].get("content") if ok else None,
            "approval_id": (v.detail.get("approval_id") if v else None) if not ok else None,
            "message": v.reason if v else "", "steps": []}


@router.post("/admin/demo/attack")
def start_demo_attack(http: HttpRequest):
    """The Playground's "Run test attack": starts the staged attack demo in the background, one request at a time."""
    demo = _services(http).attack_demo
    if demo is None:
        return JSONResponse({"error": {"message": "the attack demo needs a demo harness behind the gateway"}}, status_code=501)
    if not demo.start():
        return JSONResponse({"error": {"message": "an attack run is already going"}, **demo.status()}, status_code=409)
    return JSONResponse(demo.status(), status_code=202)


@router.get("/admin/demo/attack")
def demo_attack_status(http: HttpRequest):
    demo = _services(http).attack_demo
    if demo is None:
        return {"state": "unavailable", "sent": 0, "current": None, "summary": None, "error": None}
    return demo.status()


@router.get("/admin/stream")
def stream(http: HttpRequest):
    audit = _services(http).audit
    q = audit.subscribe()

    def gen():
        try:
            yield ": connected\n\n"
            while True:
                try:
                    yield sse_line(q.get(timeout=15))
                except queue.Empty:
                    yield ": ping\n\n"
        finally:
            audit.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
