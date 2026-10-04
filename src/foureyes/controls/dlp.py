from __future__ import annotations

import json

from foureyes.core.actions import classify_action
from foureyes.core.control import Control, register
from foureyes.core.types import SEVERITY, Verdict
from foureyes.detect.patterns import drop_keys, find_all, redact_obj, redact_text

PII = ["pesel", "iban", "passport"]
OWASP = ("LLM02:2026",)


@register
class DlpControl(Control):
    """In-flight handling, scoped to four tasks. PII the task needs is routed local, not redacted."""
    id = "dlp.redact_inflight"
    phases = ("pre", "post")

    def _mode(self, ctx, kind: str) -> str:
        return "monitor" if self.monitoring else ctx.policy.dlp_value(kind, "on_detect", "redact")

    def _handle(self, ctx, kind: str, label: str, apply) -> Verdict | None:
        mode = self._mode(ctx, kind)
        if mode == "monitor":
            ctx.alert("dlp.detected", dlp=kind, found=label)
            return None
        if mode == "block":
            return Verdict.block(self.id, f"{label} must not pass ({kind})", code="DLP_BLOCKED", owasp=OWASP)
        apply()
        return Verdict.redact(self.id, f"{label} redacted in flight ({kind})", owasp=OWASP, detail={"dlp": kind})

    @staticmethod
    def _strictest(verdicts: list[Verdict]) -> Verdict | None:
        return max(verdicts, key=lambda v: SEVERITY[v.outcome]) if verdicts else None

    def evaluate(self, ctx, phase):
        return self._pre(ctx) if phase == "pre" else self._post(ctx)

    def _pre(self, ctx):
        req, out = ctx.request, []
        text = req.full_text if req.kind == "model" else req.args_json
        if find_all(text, ["secrets"]):
            v = self._handle(ctx, "secrets", "secret", lambda: req.map_text(lambda s: redact_text(s, ["secrets"])[0]))
            if v:
                out.append(v)
        if classify_action(ctx) == "egress":
            kinds = sorted({s.kind for s in find_all(req.args_json, PII)})
            if kinds:
                v = self._handle(ctx, "egress_sinks", ", ".join(kinds),
                                 lambda: req.map_text(lambda s: redact_text(s, PII)[0]))
                if v:
                    out.append(v)
        return self._strictest(out)

    def _post(self, ctx):
        req, out = ctx.request, []
        if req.kind == "tool" and ctx.result is not None:
            fields = ctx.policy.source_for(ctx.source or f"mcp:{req.tool}")["redact_fields"]
            if fields:
                cleaned, removed = drop_keys(ctx.result, fields)
                if removed:
                    mode = self._mode(ctx, "field_minimization")
                    if mode == "block":
                        out.append(Verdict.block(self.id, "restricted fields in tool result", code="DLP_BLOCKED", owasp=OWASP))
                    elif mode == "redact":
                        ctx.result = cleaned
                        out.append(Verdict.redact(self.id, f"{removed} field(s) removed before the model sees them",
                                                  owasp=OWASP, detail={"dlp": "field_minimization", "removed": removed}))
                    else:
                        ctx.alert("dlp.detected", dlp="field_minimization", found=removed)
            if find_all(json.dumps(ctx.result, ensure_ascii=False, default=str), ["secrets"]):
                def apply():
                    ctx.result, _ = redact_obj(ctx.result, ["secrets"])
                v = self._handle(ctx, "secrets", "secret in tool result", apply)
                if v:
                    out.append(v)
        if req.kind == "model" and ctx.response_text and find_all(ctx.response_text, ["secrets"]):
            def apply_text():
                ctx.response_text = redact_text(ctx.response_text, ["secrets"])[0]
            v = self._handle(ctx, "secrets", "secret in model answer", apply_text)
            if v:
                out.append(v)
        return self._strictest(out)
