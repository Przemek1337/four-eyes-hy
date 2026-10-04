from foureyes.core.control import Control, register
from foureyes.core.types import Verdict


@register
class ModelsAllowlist(Control):
    id = "models.allowlist"
    phases = ("pre",)

    def evaluate(self, ctx, phase):
        req = ctx.request
        if req.kind != "model" or (req.model or "auto") == "auto":
            return None
        if ctx.policy.model_provider(req.model) is None:
            return Verdict.block(self.id, f"model {req.model!r} is not allowed", code="MODEL_NOT_ALLOWED",
                                 owasp=("LLM03:2026",))
        return None
