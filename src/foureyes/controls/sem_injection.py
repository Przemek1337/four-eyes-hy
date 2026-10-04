from __future__ import annotations

import json

from foureyes.core.control import Control, register
from foureyes.core.types import Verdict
from foureyes.semantic.rule_based_injection_scorer import assess_injection

OWASP = ("LLM01:2026", "ASI01")
LEGACY = (None, "promptguard")


@register
class PromptInjectionControl(Control):
    id = "sem.prompt_injection"
    phases = ("pre", "post")
    layer = "ai"

    def _flag(self, ctx, reason: str, **data) -> None:
        ctx.session.add_label("high_risk", reason)
        ctx.alert("document.injection", owasp=list(OWASP), **data)

    def _assess(self, ctx, conf: dict, text: str) -> tuple[float, dict | None]:
        name = conf.get("model")
        registry = getattr(ctx.services, "decision_models", None)
        if registry is None or name in LEGACY:
            return float(ctx.services.injection.score(text)), None
        a = assess_injection(registry.client(name, ctx.policy), name, text, conf)
        return a.score, a.to_dict()

    def evaluate(self, ctx, phase):
        req, conf = ctx.request, self.conf(ctx)
        if phase == "pre" and req.kind == "model":
            text, is_document = req.prompt_text, req.channel == "document"
            if not text.strip():
                return None
        elif phase == "post" and req.kind == "tool" and ctx.result is not None and "untrusted" in ctx.source_labels:
            text, is_document = json.dumps(ctx.result, ensure_ascii=False, default=str), True
        else:
            return None

        try:
            score, ai = self._assess(ctx, conf, text)
        except Exception as exc:
            if is_document:
                self._flag(ctx, "injection detector unavailable on document", error=str(exc))
                return None
            if conf.get("on_error", "fail_closed") == "fail_closed":
                return Verdict.block(self.id, f"injection detector unavailable: {exc}", code="DETECTOR_UNAVAILABLE",
                                     layer="ai", owasp=OWASP)
            return None

        ctx.notes["injection_score"] = score
        extra = {"ai": ai} if ai else {}
        if ai:
            ctx.notes.setdefault("ai", {})[self.id] = ai
        rule = f", rule {ai['rule']}" if ai and ai.get("rule") else ""
        if is_document:
            if score >= conf.get("documents", {}).get("flag_above", 0.5):
                self._flag(ctx, f"document scored {score:.2f}{rule}", score=score, fragment=text[:300], **extra)
            return None
        prompts = conf.get("prompts", {})
        if score >= prompts.get("block_above", 0.8):
            return Verdict.block(self.id, f"prompt injection detected (score {score:.2f}{rule})", code="PROMPT_INJECTION",
                                 layer="ai", owasp=OWASP, detail={"score": score, "evidence": text[:200], **extra})
        if score >= prompts.get("log_above", 0.5):
            ctx.alert("prompt.suspicious", score=score, **extra)
        return None
