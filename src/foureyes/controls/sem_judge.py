from __future__ import annotations

from foureyes.core.actions import classify_action
from foureyes.core.control import Control, register
from foureyes.core.types import Outcome, Verdict
from foureyes.semantic.decision_model_action_judge import DecisionModelActionJudge
from foureyes.semantic.decision_model_client import UncertainDecision

OWASP = ("LLM01:2026", "LLM03:2026", "ASI09")
LEGACY = (None, "ollama")


@register
class ActionJudgeControl(Control):
    id = "sem.action_judge"
    phases = ("pre",)
    layer = "ai"

    def _judge(self, ctx, conf):
        name = conf.get("model")
        registry = getattr(ctx.services, "decision_models", None)
        if registry is None or name in LEGACY:
            return ctx.services.judge
        return DecisionModelActionJudge(registry.client(name, ctx.policy), name, conf)

    def _on_error(self, conf) -> Outcome:
        return Outcome.BLOCK if conf.get("on_error", "approval") == "block" else Outcome.APPROVAL

    def evaluate(self, ctx, phase):
        kind = classify_action(ctx)
        conf = self.conf(ctx)

        if kind is None or kind not in conf.get("on", ["egress", "critical"]):
            return None
        req = ctx.request
        judge = None
        try:
            judge = self._judge(ctx, conf)
            res = judge.judge(ctx.session.task or "", req.tool, req.args, sorted(ctx.session.labels))
        except UncertainDecision as unsure:
            ai = unsure.assessment.to_dict()
            ctx.notes.setdefault("ai", {})[self.id] = ai
            return Verdict(self._on_error(conf), self.id,
                           f"action judge is not confident ({unsure.assessment.confidence:.2f})", layer="ai",
                           code="JUDGE_UNCERTAIN", owasp=OWASP, detail={"ai": ai})
        except Exception as exc:
            return Verdict(self._on_error(conf), self.id, f"action judge unavailable: {exc}", layer="ai",
                           code="JUDGE_UNAVAILABLE", owasp=OWASP)
        info = res.to_dict()
        assessment = getattr(judge, "last_assessment", None)
        extra = {"ai": assessment.to_dict()} if assessment else {}
        if assessment:
            ctx.notes.setdefault("ai", {})[self.id] = extra["ai"]
        if not res.consistent and res.score >= conf.get("escalate_above", 0.7):
            action = conf.get("action", "approval")
            if action == "monitor":
                ctx.alert("judge.inconsistent", **info)
                return Verdict.allow(self.id, res.reason, layer="ai", owasp=OWASP, detail={"judge": info, **extra})
            outcome = Outcome.BLOCK if action == "block" else Outcome.APPROVAL
            return Verdict(outcome, self.id, f"action inconsistent with the task: {res.reason}", layer="ai",
                           code="ACTION_INCONSISTENT", owasp=OWASP, detail={"judge": info, **extra})
        return Verdict.allow(self.id, res.reason, layer="ai", owasp=OWASP, detail={"judge": info, **extra})
