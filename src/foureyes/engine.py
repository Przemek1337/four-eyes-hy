from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass, field

from foureyes.core.context import Ctx, Services
from foureyes.core.control import build_pipeline
from foureyes.core.types import Outcome, Request, Verdict
from foureyes.upstream.base import UpstreamError

import foureyes.controls  # noqa: F401  (registers all controls)


@dataclass
class GatewayResult:
    status: int
    body: dict
    outcome: Outcome
    decision_id: str
    session_id: str
    verdict: Verdict | None = None


def _status(v: Verdict) -> int:
    if v.outcome is Outcome.APPROVAL:
        return 409
    if v.code == "AUTH_FAILED":
        return 401
    if v.code in ("BUDGET_EXCEEDED",) or (v.code or "").startswith("SESSION_"):
        return 429
    return 403


class Engine:
    def __init__(self, services: Services):
        self.s = services
        self._pipes: dict[int, object] = {}
        self._lock = threading.Lock()

    # ---- setup -----------------------------------------------------------------------------
    def _pipeline(self, snap):
        with self._lock:
            pipe = self._pipes.get(snap.id)
            if pipe is None:
                pipe = build_pipeline(snap, self.s.telemetry)
                self._pipes = {snap.id: pipe}
            return pipe

    def _begin(self, req: Request):
        self.s.policy_store.reload_if_changed()
        snap = self.s.policy_store.current()
        sess = self.s.sessions.get_or_create(req.session_id, req.agent_id or "unknown", snap.class_order[0])
        if not sess.scope and isinstance(req.meta.get("scope"), dict):
            sess.scope = {k: str(v) for k, v in req.meta["scope"].items()}
        if req.meta.get("task") and not sess.task:
            sess.task = str(req.meta["task"])
        if req.meta.get("sensitive_terms"):
            sess.sensitive_terms = sorted(set(sess.sensitive_terms) | set(map(str, req.meta["sensitive_terms"])))
        sess.bump_steps()
        return Ctx(request=req, policy=snap, session=sess, services=self.s), self._pipeline(snap)

    # ---- helpers ---------------------------------------------------------------------------
    def _flush_session_events(self, ctx: Ctx) -> None:
        for ev in ctx.session.drain_events():
            self.s.audit.emit(ev)

    @staticmethod
    def _judge(ctx: Ctx, v: Verdict) -> dict | None:
        info = v.detail.get("judge") or next((x.detail["judge"] for x in ctx.verdicts if x.detail.get("judge")), None)
        return {"score": info["score"], "reason": info["reason"]} if info else None

    @staticmethod
    def _evidence(ctx: Ctx, v: Verdict) -> str | None:
        ev = v.detail.get("evidence") or v.detail.get("fragment")
        if ev is None:
            ev = next((a.get("fragment") or a.get("evidence") for a in ctx.alerts
                       if a.get("fragment") or a.get("evidence")), None)
        return str(ev)[:300] if ev else None

    def _event(self, ctx: Ctx, v: Verdict, total_ms: float, up_ms: float) -> dict:
        req, route = ctx.request, ctx.route
        served = ctx.notes.get("served_model")
        resource = req.tool if req.kind == "tool" else (served or (route.model if route else req.model))
        return {
            "event": "decision", "decision_id": ctx.decision_id, "session_id": req.session_id,
            "agent": req.agent_id, "kind": req.kind, "action": f"{req.kind}:{resource}", "resource": resource,
            "decision": v.outcome.value, "rule": v.rule, "reason": v.reason, "layer": v.layer, "code": v.code,
            "owasp": list(v.owasp), "signature_id": v.signature_id,
            "labels": sorted(ctx.session.labels), "data_class": ctx.session.data_class,
            "latency_ms": round(total_ms, 3), "gateway_ms": round(total_ms - up_ms, 3), "upstream_ms": round(up_ms, 3),
            "timings": ctx.spans,
            "route": ({"allowed": route.allowed_types, "chosen": route.type, "model": route.model,
                       "served_model": served, "router": route.router, "rerouted_from": route.rerouted_from,
                       "fallback": route.fallback}
                      if route else None),
            "upstream_type": route.type if route else None, "provider": route.type if route else None,
            "anonymization": ctx.notes.get("anonymization"),
            "tokens": ctx.usage.get("total_tokens", 0), "cost_usd": ctx.notes.get("cost_usd", 0.0),
            "compute_s": ctx.notes.get("compute_s", 0.0),
            "alerts": ctx.alerts, "monitor": [{"rule": m.rule, "outcome": m.outcome.value} for m in ctx.monitor],
            "detail": v.detail,
            "injection_score": ctx.notes.get("injection_score"),
            "ai": ctx.notes.get("ai"),
            "reference": v.detail.get("reference"),
            "judge": self._judge(ctx, v),
            "evidence": self._evidence(ctx, v),
            "content": req.prompt_text[:500] if req.kind == "model" else req.args_json[:500],
        }

    def _finish(self, ctx: Ctx, v: Verdict, t0: float, up_ms: float = 0.0) -> None:
        total_ms = (time.perf_counter() - t0) * 1000
        self.s.telemetry.record_request(total_ms - up_ms, up_ms)
        self._flush_session_events(ctx)
        self.s.audit.emit(self._event(ctx, v, total_ms, up_ms))

    def _reject(self, ctx: Ctx, v: Verdict, t0: float, up_ms: float = 0.0) -> GatewayResult:
        self._finish(ctx, v, t0, up_ms)
        err = {"type": "foureyes_approval" if v.outcome is Outcome.APPROVAL else "foureyes_block",
               "code": v.code or ("APPROVAL_REQUIRED" if v.outcome is Outcome.APPROVAL else "BLOCKED"),
               "message": v.reason, "rule": v.rule, "decision": v.outcome.value,
               "decision_id": ctx.decision_id, "session_id": ctx.request.session_id}
        if v.detail.get("approval_id"):
            err["approval_id"] = v.detail["approval_id"]
        return GatewayResult(_status(v), {"error": err}, v.outcome, ctx.decision_id, ctx.request.session_id, v)

    def _approval_gate(self, ctx: Ctx, v: Verdict, tool: str, args: dict) -> Verdict:
        req, svc = ctx.request, self.s.approvals
        approval_id = req.meta.get("approval_id")
        if approval_id:
            r = svc.redeem(approval_id, req.session_id, req.agent_id, tool, args)
            if r.code == "ok":
                return Verdict.allow("approval.redeemed", f"approved by {r.approval.decided_by}",
                                     detail={"approval_id": approval_id})
            if r.code != "pending":
                return Verdict.block("approval.binding", f"approval cannot be used: {r.code}", code=r.code,
                                     owasp=("ASI09",), detail={"approval_id": approval_id})
            a = r.approval
        else:
            judge = next((x.detail["judge"] for x in ctx.verdicts if "judge" in x.detail), None)
            a = svc.request(session_id=req.session_id, agent_id=req.agent_id, tool=tool, args=args, rule=v.rule,
                            reason=v.reason, labels=list(ctx.session.labels), data_class=ctx.session.data_class,
                            judge=judge, supplied_reason=req.meta.get("reason"))
        return Verdict(Outcome.APPROVAL, v.rule, v.reason, layer=v.layer, code="APPROVAL_REQUIRED", owasp=v.owasp,
                       detail={**v.detail, "approval_id": a.id, "params_hash": a.hash})

    @staticmethod
    def _stricter(a: Verdict, b: Verdict) -> Verdict:
        return b if b.stricter_than(a) else a

    # ---- model calls -----------------------------------------------------------------------
    def handle_model(self, req: Request) -> GatewayResult:
        t0 = time.perf_counter()
        ctx, pipe = self._begin(req)
        v = pipe.run(ctx, "pre")
        if v.outcome is Outcome.APPROVAL:
            digest = hashlib.sha256(req.full_text.encode()).hexdigest()
            v = self._approval_gate(ctx, v, "model.chat", {"model": ctx.route.model if ctx.route else req.model,
                                                           "messages_sha256": digest})
        if v.outcome in (Outcome.BLOCK, Outcome.APPROVAL):
            return self._reject(ctx, v, t0)

        ctx.notes.update(self.s.anonymizer.process(ctx.route.type))
        upstream = self.s.upstreams.models.get(ctx.route.provider)
        if upstream is None:
            return self._reject(ctx, Verdict.block("route.upstream", f"no upstream for {ctx.route.provider}",
                                                   code="UPSTREAM_ERROR"), t0)
        params = {k: val for k, val in req.params.items() if k != "tools"}
        t_up = time.perf_counter()
        try:
            resp = upstream.chat(ctx.route.model, req.messages, tools=req.params.get("tools"), **params)
        except UpstreamError as exc:
            up_ms = (time.perf_counter() - t_up) * 1000
            private = ctx.session.data_class != ctx.policy.class_order[0]
            code = "LOCAL_UNAVAILABLE" if ctx.route.type == "local" and private else "UPSTREAM_ERROR"
            return self._reject(ctx, Verdict.block("route.upstream", str(exc), code=code, owasp=("LLM02:2026",)), t0, up_ms)
        up_ms = (time.perf_counter() - t_up) * 1000
        ctx.usage, ctx.upstream_seconds = resp.usage, resp.seconds
        if resp.served_model:
            ctx.notes["served_model"] = resp.served_model  # what really answered, not what the policy asked for
        content = resp.message.get("content")
        ctx.response_text = content if isinstance(content, str) else None

        post = pipe.run(ctx, "post")
        if post.outcome in (Outcome.BLOCK, Outcome.APPROVAL):
            return self._reject(ctx, post, t0, up_ms)
        final = self._stricter(v, post)
        message = dict(resp.message)
        if ctx.response_text is not None:
            message["content"] = ctx.response_text
        self._finish(ctx, final, t0, up_ms)
        route = ctx.route
        body = {
            "id": f"chatcmpl-{ctx.decision_id}", "object": "chat.completion", "model": resp.served_model or route.model,
            "choices": [{"index": 0, "message": message,
                         "finish_reason": "tool_calls" if message.get("tool_calls") else "stop"}],
            "usage": resp.usage,
            "foureyes": {"decision_id": ctx.decision_id, "decision": final.outcome.value, "rule": final.rule,
                         "session_id": req.session_id, "data_class": ctx.session.data_class,
                         "route": {"type": route.type, "model": route.model, "served_model": resp.served_model,
                                   "router": route.router, "rerouted_from": route.rerouted_from}},
        }
        return GatewayResult(200, body, final.outcome, ctx.decision_id, req.session_id, final)

    # ---- tool calls ------------------------------------------------------------------------
    def list_tools(self, agent_id: str | None) -> list[dict]:
        snap = self.s.policy_store.current()
        allowed = snap.agents.get(agent_id or "", {}).get("tools", [])
        tools = self.s.upstreams.tools.list_tools() if self.s.upstreams.tools else []
        return [t for t in tools if t["name"] in allowed]

    @staticmethod
    def _note_subjects(ctx, req) -> None:
        """Remember whom a screening tool cleared and which name an entity was created for (policy: tools.<t>.screens / creates_entity)."""
        cfg = ctx.policy.tools.get(req.tool, {})
        from foureyes.controls.tools import fold
        if cfg.get("screens") and req.args.get(cfg["screens"]):
            ctx.session.note_screened(fold(req.args[cfg["screens"]]))
        made = cfg.get("creates_entity")
        if made and isinstance(ctx.result, dict) and ctx.result.get(made["id_result"]) and req.args.get(made["name_arg"]):
            ctx.session.note_entity(str(ctx.result[made["id_result"]]), fold(req.args[made["name_arg"]]))

    def handle_tool(self, req: Request) -> GatewayResult:
        t0 = time.perf_counter()
        ctx, pipe = self._begin(req)
        v = pipe.run(ctx, "pre")
        if v.outcome is Outcome.APPROVAL:
            v = self._approval_gate(ctx, v, req.tool, req.args)
        if v.outcome in (Outcome.BLOCK, Outcome.APPROVAL):
            return self._reject(ctx, v, t0)
        if self.s.upstreams.tools is None:
            return self._reject(ctx, Verdict.block("route.upstream", "no tool server configured", code="UPSTREAM_ERROR"), t0)
        t_up = time.perf_counter()
        try:
            ctx.result = self.s.upstreams.tools.call(req.tool, req.args)
        except (UpstreamError, TypeError) as exc:
            up_ms = (time.perf_counter() - t_up) * 1000
            return self._reject(ctx, Verdict.block("route.upstream", str(exc), code="UPSTREAM_ERROR"), t0, up_ms)
        up_ms = (time.perf_counter() - t_up) * 1000
        ctx.session.note_tool(req.tool)
        self._note_subjects(ctx, req)

        post = pipe.run(ctx, "post")
        if post.outcome in (Outcome.BLOCK, Outcome.APPROVAL):
            return self._reject(ctx, post, t0, up_ms)
        final = self._stricter(v, post)
        self._finish(ctx, final, t0, up_ms)
        body = {"result": ctx.result,
                "foureyes": {"decision_id": ctx.decision_id, "decision": final.outcome.value, "rule": final.rule,
                             "session_id": req.session_id, "data_class": ctx.session.data_class}}
        return GatewayResult(200, body, final.outcome, ctx.decision_id, req.session_id, final)
