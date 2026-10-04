import re

from foureyes.core.control import Control, register
from foureyes.core.types import Verdict


def fold(value) -> str:
    return re.sub(r"[\W_]+", "", str(value)).casefold()


def same_subject(a: str, b: str) -> bool:
    """'Acme' and 'Acme Ltd' are one subject; 'Acme' and 'Borealis' are not (a model may drop the legal form)."""
    return bool(a and b) and (a == b or (min(len(a), len(b)) >= 5 and (a in b or b in a)))


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
        cfg = ctx.policy.tools.get(req.tool, {})
        missing = [t for t in cfg.get("requires_before", []) if t not in ctx.session.tools_called]
        if missing:
            return Verdict.block(self.id, f"{req.tool} requires {', '.join(missing)} first",
                                 code="TOOL_ORDER", owasp=("LLM03:2026", "ASI02"))
        rule = cfg.get("requires_screened_subject")
        return self._screened(ctx, req, rule) if rule else None

    def _screened(self, ctx, req, rule):
        """The screening must be of the subject this call acts on, not of any name the agent chose."""
        session = ctx.session
        subject = session.entities.get(str(req.args.get(rule.get("entity_arg", "entity_id"), "")))
        if subject is not None:
            ok = any(same_subject(subject, name) for name in session.screened)
        else:  # an entity this session did not create: the case subject from the task must have been screened
            task = fold(session.task or "")
            ok = any(same_subject(name, task) for name in session.screened)
        if ok:
            return None
        return Verdict.block(self.id, f"{req.tool}: the screening in this session was not for the subject of this call",
                             code="SCREENING_SUBJECT_MISMATCH", owasp=("LLM03:2026", "ASI02"))
