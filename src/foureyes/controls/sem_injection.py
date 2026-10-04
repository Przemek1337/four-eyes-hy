from __future__ import annotations

import json

from foureyes.core.control import Control, register
from foureyes.core.types import Verdict

OWASP = ("LLM01:2026", "ASI01")


@register
class PromptInjectionControl(Control):
    id = "sem.prompt_injection"
    phases = ("pre", "post")
    layer = "ai"

    def _flag(self, ctx, reason: str, **data) -> None:
        ctx.session.add_label("high_risk", reason)
        ctx.alert("document.injection", owasp=list(OWASP), **data)

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
            score = ctx.services.injection.score(text)
        except Exception as exc:
            if is_document:
                self._flag(ctx, "injection detector unavailable on document", error=str(exc))
                return None
            if conf.get("on_error", "fail_closed") == "fail_closed":
                return Verdict.block(self.id, f"injection detector unavailable: {exc}", code="DETECTOR_UNAVAILABLE",
                                     layer="ai", owasp=OWASP)
            return None

        ctx.notes["injection_score"] = score
        if is_document:
            if score >= conf.get("documents", {}).get("flag_above", 0.5):
                self._flag(ctx, f"document scored {score:.2f}", score=score, fragment=text[:300])
            return None
        prompts = conf.get("prompts", {})
        if score >= prompts.get("block_above", 0.8):
            return Verdict.block(self.id, f"prompt injection detected (score {score:.2f})", code="PROMPT_INJECTION",
                                 layer="ai", owasp=OWASP, detail={"score": score, "evidence": text[:200]})
        if score >= prompts.get("log_above", 0.5):
            ctx.alert("prompt.suspicious", score=score)
        return None
