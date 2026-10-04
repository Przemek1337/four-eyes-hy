from foureyes.core.control import Control, register
from foureyes.core.types import Verdict

OWASP = ("LLM09:2026",)


@register
class ScopeControl(Control):
    id = "authz.scope"
    phases = ("pre", "post")

    def evaluate(self, ctx, phase):
        req = ctx.request
        scope_cfg = ctx.agent_cfg().get("scope")
        if not scope_cfg or req.kind != "tool":
            return None
        key = scope_cfg["key"]
        want = ctx.session.scope.get(key)
        tool_cfg = ctx.policy.tools.get(req.tool, {})
        filt = tool_cfg.get("filter_by")

        if phase == "pre":
            if filt and want is None:
                return Verdict.block(self.id, f"session has no {key}; cannot enforce scope", code="SCOPE_UNKNOWN", owasp=OWASP)
            if filt and filt not in req.args:
                return Verdict.block(self.id, f"{req.tool} must be called with {filt}", code="SCOPE_FILTER_MISSING", owasp=OWASP)
            for k in {key, filt} - {None}:
                if k in req.args and want is not None and str(req.args[k]) != str(want):
                    return Verdict.block(self.id, f"{k} {req.args[k]!r} is outside this session's scope",
                                         code="SCOPE_VIOLATION", owasp=OWASP)
            return None

        if filt and isinstance(ctx.result, dict) and isinstance(ctx.result.get("results"), list):
            kept = [r for r in ctx.result["results"] if isinstance(r, dict) and str(r.get(key)) == str(want)]
            removed = len(ctx.result["results"]) - len(kept)
            if removed:
                ctx.result = {**ctx.result, "results": kept}
                return Verdict.redact(self.id, f"removed {removed} result(s) from other scopes",
                                      owasp=OWASP, detail={"removed": removed})
        return None
