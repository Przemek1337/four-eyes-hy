from __future__ import annotations

import re

from foureyes.core.control import Control, register
from foureyes.core.types import Verdict
from foureyes.detect.normalize import variants
from foureyes.signatures.matchers import host_of

MD = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)([^)]*)\)")
SCRIPT = re.compile(r"<\s*(script|iframe|object|embed)\b.*?(?:</\s*\1\s*>|$)", re.I | re.S)
JS_URL = re.compile(r"javascript\s*:", re.I)
REF_DEF = re.compile(r"^([ \t]{0,3}\[[^\]\n]+\]:[ \t]*)<?(\S+?)>?([ \t].*)?$", re.M)
AUTOLINK = re.compile(r"<((?:https?:)?//[^\s<>]+)>", re.I)
TAG = re.compile(r"<\s*/?\s*([a-zA-Z][\w:-]*)([^<>]*)>")
ATTR_URL = re.compile(r"""\b(?:src|href|srcset|action|formaction|poster|data|background|xlink:href|content)\s*=\s*["']?\s*([^\s"'>]+)""", re.I)
EVENT_ATTR = re.compile(r"[\s/\"']on[a-z]+\s*=", re.I)
DANGEROUS_TAGS = {"script", "iframe", "object", "embed", "svg", "math", "style", "link", "meta", "base", "form",
                  "frame", "frameset", "applet"}


def _squash(text: str) -> str:
    return re.sub(r"[\W_]+", "", text).casefold()


@register
class OutputSafe(Control):
    id = "output.safe"
    phases = ("post",)

    def evaluate(self, ctx, phase):
        if ctx.request.kind != "model" or not ctx.response_text:
            return None
        conf, text = self.conf(ctx), ctx.response_text
        canary = conf.get("canary")
        if canary and any(_squash(canary) in _squash(v) for v in variants(text)):  # case, spacing, zero-width, base64
            if self.monitoring:
                ctx.alert("output.canary", canary=True)
            else:
                return Verdict.block(self.id, "system prompt canary found in the answer", code="CANARY_LEAK",
                                     owasp=("LLM08:2026",))
        allowed = [d.lower() for d in conf.get("allowed_domains", [])]
        foreign: list[str] = []
        html: list[str] = []

        def is_foreign(url: str) -> str | None:
            host = host_of(url)
            if host and not any(host == a or host.endswith("." + a) for a in allowed):
                return host
            return None

        def swap(m: re.Match) -> str:
            host = is_foreign(m.group(3))
            if host:
                foreign.append(host)
                return m.group(2) or ("[image removed]" if m.group(1) else "[link removed]")
            return m.group(0)

        def swap_ref(m: re.Match) -> str:
            host = is_foreign(m.group(2))
            if host:
                foreign.append(host)
                return "[link removed]"
            return m.group(0)

        def swap_url(m: re.Match) -> str:
            host = is_foreign(m.group(1))
            if host:
                foreign.append(host)
                return "[link removed]"
            return m.group(0)

        def swap_tag(m: re.Match) -> str:
            name, attrs = m.group(1).lower(), m.group(2)
            bad_url = next((h for u in ATTR_URL.findall(attrs) if (h := is_foreign(u))), None)
            if name in DANGEROUS_TAGS or EVENT_ATTR.search(" " + attrs) or bad_url or JS_URL.search(attrs):
                html.append(bad_url or "html/script")
                return ""
            return m.group(0)

        cleaned = MD.sub(swap, text)
        cleaned = REF_DEF.sub(swap_ref, cleaned)
        cleaned = AUTOLINK.sub(swap_url, cleaned)
        cleaned, n_script = SCRIPT.subn("", cleaned)
        cleaned = TAG.sub(swap_tag, cleaned)
        cleaned, n_js = JS_URL.subn("blocked:", cleaned)
        if not foreign and not html and not n_script and not n_js:
            return None
        found = sorted(set(foreign) | {h for h in html if h != "html/script"}) + (
            ["html/script"] if n_script or n_js or "html/script" in html else [])
        if self.monitoring:
            ctx.alert("output.unsafe", found=found)
            return None
        if conf.get("mode", self.mode) == "block":
            return Verdict.block(self.id, f"unsafe content in the answer: {', '.join(found)}", code="UNSAFE_OUTPUT",
                                 owasp=("LLM10:2026",))
        ctx.response_text = cleaned
        return Verdict.redact(self.id, f"removed unsafe content: {', '.join(found)}", owasp=("LLM10:2026",),
                              detail={"removed": found})
