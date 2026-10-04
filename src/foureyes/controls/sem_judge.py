from __future__ import annotations

from foureyes.core.actions import classify_action
from foureyes.core.control import Control, register
from foureyes.core.types import Outcome, Verdict

OWASP = ("LLM01:2026", "LLM03:2026", "ASI09")


@register
class ActionJudgeControl(Control):
    id = "sem.action_judge"
    phases = ("pre",)
    layer = "ai"

    def evaluate(self, ctx, phase):
        kind = classify_action(ctx)
        conf = self.conf(ctx)
        if kind is None or kind not in conf.get("on", ["egress", "critical"]):
            return None
        req = ctx.request
        try:
            res = ctx.services.judge.judge(ctx.session.task or "", req.tool, req.args, sorted(ctx.session.labels))
        except Exception as exc:
            action = conf.get("on_error", "approval")
            outcome = Outcome.BLOCK if action == "block" else Outcome.APPROVAL
            return Verdict(outcome, self.id, f"action judge unavailable: {exc}", layer="ai",
                           code="JUDGE_UNAVAILABLE", owasp=OWASP)
        info = res.to_dict()
        if not res.consistent and res.score >= conf.get("escalate_above", 0.7):
            action = conf.get("action", "approval")
            if action == "monitor":
                ctx.alert("judge.inconsistent", **info)
                return Verdict.allow(self.id, res.reason, layer="ai", owasp=OWASP, detail={"judge": info})
            outcome = Outcome.BLOCK if action == "block" else Outcome.APPROVAL
            return Verdict(outcome, self.id, f"action inconsistent with the task: {res.reason}", layer="ai",
                           code="ACTION_INCONSISTENT", owasp=OWASP, detail={"judge": info})
        return Verdict.allow(self.id, res.reason, layer="ai", owasp=OWASP, detail={"judge": info})
