from foureyes.core.actions import classify_action
from foureyes.core.control import Control, register
from foureyes.core.types import SEVERITY, Outcome, Verdict

OUTCOMES = {"ALLOW": Outcome.ALLOW, "ALLOW_LOG": Outcome.ALLOW, "APPROVAL": Outcome.APPROVAL, "BLOCK": Outcome.BLOCK}
OWASP = ("LLM01:2026", "LLM05:2026", "ASI01")


@register
class FlowUntrusted(Control):
    id = "flow.untrusted"
    phases = ("pre",)

    def evaluate(self, ctx, phase):
        kind = classify_action(ctx)
        if kind is None:
            return None
        profile = ctx.profile()
        worst: Verdict | None = None
        for rule in ctx.policy.labels.get("rules", []):
            if rule["when"]["session"] not in ctx.session.labels:
                continue
            spec = rule.get(kind)
            if isinstance(spec, dict):
                spec = spec.get(profile)
            if spec is None:
                continue
            v = Verdict(OUTCOMES[spec], rule["id"],
                        f"{kind} action in a {rule['when']['session']} session ({profile} profile)",
                        owasp=OWASP, detail={"action_kind": kind})
            if worst is None or SEVERITY[v.outcome] > SEVERITY[worst.outcome]:
                worst = v
        return worst
