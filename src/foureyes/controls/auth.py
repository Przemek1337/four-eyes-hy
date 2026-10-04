from foureyes.core.control import Control, register
from foureyes.core.types import Verdict


@register
class AgentKeyControl(Control):
    id = "auth.agent_key"
    phases = ("pre",)

    def evaluate(self, ctx, phase):
        aid = ctx.request.agent_id
        if aid and aid in ctx.policy.agents:
            return None
        return Verdict.block(self.id, "missing or invalid agent key", code="AUTH_FAILED",
                             owasp=("LLM03:2026", "ASI03"))
