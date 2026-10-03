from foureyes.core.control import Control, register
from foureyes.core.types import Verdict
from foureyes.detect.patterns import find_all, redact_text

PII = ["pesel", "iban", "passport"]


@register
class ClassifyNetControl(Control):
    """Safety net for data that arrived without a label. Can only raise the class, never lower it."""
    id = "data.classify_net"
    phases = ("pre",)

    def evaluate(self, ctx, phase):
        text = ctx.request.full_text if ctx.request.kind == "model" else ctx.request.args_json
        kinds = sorted({s.kind for s in find_all(text, PII)})
        lowered = text.lower()
        if any(t and t.lower() in lowered for t in ctx.session.sensitive_terms):
            kinds.append("sensitive_term")
        if not kinds:
            return None
        action = ctx.policy.dlp_value("pii_in_prompt", "on_detect", "raise_class")
        if self.monitoring or action == "monitor":
            ctx.alert("pii.detected", kinds=kinds)
            return None
        owasp = ("LLM02:2026",)
        if action == "block":
            return Verdict.block(self.id, f"personal data detected ({', '.join(kinds)})", code="PII_BLOCKED", owasp=owasp)
        if action == "redact":
            ctx.request.map_text(lambda s: redact_text(s, PII)[0])
            return Verdict.redact(self.id, f"personal data redacted ({', '.join(kinds)})", owasp=owasp)
        order = ctx.policy.class_order
        target = self.cfg.get("raise_to") or order[1]
        ctx.session.raise_class(target, order, f"detected {', '.join(kinds)}", "detector")
        return Verdict.allow(self.id, f"detected {', '.join(kinds)}; session class raised to {target}", owasp=owasp)
