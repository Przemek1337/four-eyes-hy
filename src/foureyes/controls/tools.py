from foureyes.core.control import Control, register
from foureyes.core.types import Verdict


@register
class AuthzTools(Control):
    id = "authz.tools"
    phases = ("pre",)

    def evaluate(self, ctx, phase):
        req = ctx.request
        if req.kind != "tool":
            return None
        allowed = ctx.agent_cfg().get("tools", [])
        if req.tool not in allowed:
            return Verdict.block(self.id, f"tool {req.tool!r} is not permitted for agent {req.agent_id!r}",
                                 code="TOOL_NOT_ALLOWED", owasp=("LLM03:2026", "ASI02"))
        required = ctx.policy.tools.get(req.tool, {}).get("requires_before", [])
        missing = [t for t in required if t not in ctx.session.tools_called]
        if missing:
            return Verdict.block(self.id, f"{req.tool} requires {', '.join(missing)} first",
                                 code="TOOL_ORDER", owasp=("LLM03:2026", "ASI02"))
        return None
