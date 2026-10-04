import re

from jsonschema import Draft202012Validator

from foureyes.core.control import Control, register
from foureyes.core.types import Outcome, Verdict


def _field_of(error) -> str:
    if error.path:
        return str(error.path[0])
    if error.validator == "required":
        return error.message.split("'")[1]
    return "*"


def _key(name) -> str:
    """Field names compared the way a backend might read them: case, underscores and hyphens ignored."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _all_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_keys(v)


@register
class ToolSchemaControl(Control):
    id = "authz.tool_schema"
    phases = ("pre",)

    def evaluate(self, ctx, phase):
        req = ctx.request
        if req.kind != "tool":
            return None
        cfg = ctx.policy.tools.get(req.tool, {})
        present = {_key(k) for k in _all_keys(req.args)}  # case_status, Case-Status, caseStatus, nested ones too
        for name in cfg.get("cannot_change", []):
            if _key(name) in present:
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
