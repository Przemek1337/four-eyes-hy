from __future__ import annotations

import re

from foureyes.core.control import Control, register
from foureyes.core.types import Verdict
from foureyes.signatures.matchers import host_of

MD = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)([^)]*)\)")
SCRIPT = re.compile(r"<\s*(script|iframe|object|embed)\b.*?(?:</\s*\1\s*>|$)", re.I | re.S)
JS_URL = re.compile(r"javascript\s*:", re.I)


@register
class OutputSafe(Control):
    id = "output.safe"
    phases = ("post",)

    def evaluate(self, ctx, phase):
        if ctx.request.kind != "model" or not ctx.response_text:
            return None
        conf, text = self.conf(ctx), ctx.response_text
        canary = conf.get("canary")
        if canary and canary in text:
            if self.monitoring:
                ctx.alert("output.canary", canary=True)
            else:
                return Verdict.block(self.id, "system prompt canary found in the answer", code="CANARY_LEAK",
                                     owasp=("LLM08:2026",))
        allowed = [d.lower() for d in conf.get("allowed_domains", [])]
        foreign: list[str] = []

        def swap(m: re.Match) -> str:
            host = host_of(m.group(3))
            if host and not any(host == a or host.endswith("." + a) for a in allowed):
                foreign.append(host)
                return m.group(2) or ("[image removed]" if m.group(1) else "[link removed]")
            return m.group(0)

        cleaned = MD.sub(swap, text)
        cleaned, n_script = SCRIPT.subn("", cleaned)
        cleaned, n_js = JS_URL.subn("blocked:", cleaned)
        if not foreign and not n_script and not n_js:
            return None
        found = sorted(set(foreign)) + (["html/script"] if n_script or n_js else [])
        if self.monitoring:
            ctx.alert("output.unsafe", found=found)
            return None
        if conf.get("mode", self.mode) == "block":
            return Verdict.block(self.id, f"unsafe content in the answer: {', '.join(found)}", code="UNSAFE_OUTPUT",
                                 owasp=("LLM10:2026",))
        ctx.response_text = cleaned
        return Verdict.redact(self.id, f"removed unsafe content: {', '.join(found)}", owasp=("LLM10:2026",),
                              detail={"removed": found})
