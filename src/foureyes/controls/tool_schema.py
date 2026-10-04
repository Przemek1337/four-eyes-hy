from jsonschema import Draft202012Validator

from foureyes.core.control import Control, register
from foureyes.core.types import Outcome, Verdict


def _field_of(error) -> str:
    if error.path:
        return str(error.path[0])
    if error.validator == "required":
        return error.message.split("'")[1]
    return "*"


@register
class ToolSchemaControl(Control):
    id = "authz.tool_schema"
    phases = ("pre",)

    def evaluate(self, ctx, phase):
        req = ctx.request
        if req.kind != "tool":
            return None
        cfg = ctx.policy.tools.get(req.tool, {})
        for name in cfg.get("cannot_change", []):
            if name in req.args:
                return Verdict.block(self.id, f"field {name!r} cannot be changed through {req.tool}",
                                     code="FIELD_IMMUTABLE", owasp=("LLM05:2026",))
        schema = ctx.policy.tool_schema(req.tool)
        if schema is None:
            return None
        errors = list(Draft202012Validator(schema).iter_errors(req.args))
        if not errors:
            return None
        on_violation = cfg.get("on_violation", {})
        worst = Outcome.APPROVAL if all(
            on_violation.get(_field_of(e), on_violation.get("*", "block")) == "approval" for e in errors
        ) else Outcome.BLOCK
        reasons = "; ".join(e.message for e in errors[:3])
        code = "SCHEMA_APPROVAL" if worst is Outcome.APPROVAL else "SCHEMA_VIOLATION"
        return Verdict(worst, self.id, f"arguments violate schema: {reasons}", code=code,
                       owasp=("LLM03:2026", "ASI02"))
