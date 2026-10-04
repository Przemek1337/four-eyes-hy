from foureyes.core.control import Control, register
from foureyes.core.types import Outcome, Verdict
from foureyes.detect.decision_model_data_class_detector import classify_data
from foureyes.detect.patterns import find_all, redact_text

PII = ["pesel", "iban", "passport"]
OWASP = ("LLM02:2026",)


@register
class ClassifyNetControl(Control):
    """Safety net for data that arrived without a label. Can only raise the class, never lower it.
    Deterministic detectors run first; then, if configured, a decision model classifies the text."""
    id = "data.classify_net"
    phases = ("pre",)

    def evaluate(self, ctx, phase):
        text = ctx.request.full_text if ctx.request.kind == "model" else ctx.request.args_json
        det = self._deterministic(ctx, text)
        if det is not None and det.outcome is not Outcome.ALLOW:
            return det
        return self._ai(ctx, text) or det

    def _deterministic(self, ctx, text):
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
        if action == "block":
            return Verdict.block(self.id, f"personal data detected ({', '.join(kinds)})", code="PII_BLOCKED", owasp=OWASP)
        if action == "redact":
            ctx.request.map_text(lambda s: redact_text(s, PII)[0])
            return Verdict.redact(self.id, f"personal data redacted ({', '.join(kinds)})", owasp=OWASP)
        order = ctx.policy.class_order
        target = self.cfg.get("raise_to") or order[1]
        ctx.session.raise_class(target, order, f"detected {', '.join(kinds)}", "detector")
        return Verdict.allow(self.id, f"detected {', '.join(kinds)}; session class raised to {target}", owasp=OWASP)

    def _ai(self, ctx, text):
        conf = self.conf(ctx).get("ai") or {}
        registry = getattr(ctx.services, "decision_models", None)
        order = ctx.policy.class_order
        if not conf.get("model") or registry is None or not text.strip() or ctx.session.data_class == order[-1]:
            return None
        name = conf["model"]
        try:
            a = classify_data(registry.client(name, ctx.policy), name, text, conf, order)
        except Exception as exc:
            ctx.session.raise_class(order[-1], order, f"data classifier unavailable: {exc}", f"ai:{name}")
            return Verdict.allow(self.id, f"data classifier unavailable; session class raised to {order[-1]}",
                                 layer="ai", code="CLASSIFIER_UNAVAILABLE", owasp=OWASP)
        ai = a.to_dict()
        ctx.notes.setdefault("ai", {})[self.id] = ai
        if self.monitoring:
            ctx.alert("class.suggested", ai=ai)
            return None
        if ctx.session.raise_class(a.outcome, order, f"AI classified the content as {a.outcome}", f"ai:{name}"):
            return Verdict.allow(self.id, f"AI classified the content as {a.outcome}; session class raised",
                                 layer="ai", owasp=OWASP, detail={"ai": ai})
        return None
