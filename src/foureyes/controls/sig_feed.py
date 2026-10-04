from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from foureyes.core.control import Control, register
from foureyes.core.types import Verdict
from foureyes.signatures.matchers import (has_unicode_smuggling, hidden_text, host_of, scan_pickle_bytes,
                                          urls_in)

DEFAULT_SCAN = ("pkl", "pt", "bin")


@register
class SigFeedControl(Control):
    id = "sig.feed"
    phases = ("pre", "post")

    # ---- verdict builders ---------------------------------------------------------------
    def _block(self, sig: dict, reason: str, code: str, **detail) -> Verdict:
        return Verdict.block(self.id, reason, code=code, signature_id=sig["id"],
                             owasp=tuple(sig.get("owasp", ())),
                             detail={"reference": sig.get("reference"), **detail})

    def _text_hit(self, feed, text: str):
        for sig in feed.by_type("prompt_pattern"):
            for pat in sig.get("match", []):
                m = re.search(pat, text)
                if m:
                    return sig, f"prompt matches known jailbreak pattern {sig['id']}", {"evidence": m.group(0)[:200]}
        for sig in feed.by_type("unicode_smuggling"):
            if has_unicode_smuggling(text):
                return sig, "invisible Unicode characters hide text", {"evidence": hidden_text(text)[:200] or "zero-width characters"}
        return None

    def _flag_document(self, ctx, hit) -> None:
        sig, reason, detail = hit
        ctx.session.add_label("high_risk", f"{sig['id']} on document")
        ctx.alert("document.signature", signature=sig["id"], owasp=list(sig.get("owasp", ())), **detail)

    # ---- evaluate -----------------------------------------------------------------------
    def evaluate(self, ctx, phase):
        feed = ctx.services.feed
        feed.refresh_if_changed()
        req = ctx.request
        if phase == "pre":
            if req.kind == "model":
                hit = self._text_hit(feed, req.prompt_text)
                if not hit:
                    return None
                if req.channel == "document":
                    self._flag_document(ctx, hit)
                    return None
                sig, reason, detail = hit
                return self._block(sig, reason, "KNOWN_ATTACK", **detail)
            return self._tool(ctx, feed) if req.kind == "tool" else None
        if req.kind == "tool" and ctx.result is not None and "untrusted" in ctx.source_labels:
            hit = self._text_hit(feed, json.dumps(ctx.result, ensure_ascii=False))
            if hit:
                self._flag_document(ctx, hit)
            return None
        if req.kind == "model" and ctx.response_text:
            return self._urls(ctx, feed)
        return None

    def _tool(self, ctx, feed):
        req = ctx.request
        for sig in feed.by_type("tool_arg_pattern"):
            for pat in sig.get("match", []):
                m = re.search(pat, req.args_json)
                if m:
                    return self._block(sig, f"tool arguments match code-execution pattern {sig['id']}",
                                       "TOOL_ARG_SIGNATURE", evidence=m.group(0)[:200])
        if ctx.policy.tools.get(req.tool, {}).get("artifact"):
            return self._artifact(ctx, feed)
        return None

    def _artifact(self, ctx, feed):
        args = ctx.request.args
        path = Path(str(args.get("path", "")))
        if not path.is_file():
            return Verdict.block(self.id, f"artifact {path} not found", code="ARTIFACT_NOT_FOUND",
                                 owasp=("LLM04:2026", "ASI04"))
        data = path.read_bytes()  # bytes only; never unpickled
        digest = hashlib.sha256(data).hexdigest()
        for sig in feed.by_type("file_hash"):
            if digest in sig.get("match", []):
                return self._block(sig, "artifact hash is on the known-malicious list", "KNOWN_MALICIOUS_ARTIFACT", sha256=digest)
        ext = path.suffix.lstrip(".").lower()
        scan_formats = DEFAULT_SCAN
        for sig in feed.by_type("model_source"):
            source = args.get("source")
            if source and not any(source.startswith(p) for p in sig.get("allowed_sources", [])):
                return self._block(sig, f"model source {source!r} is not allowed", "MODEL_SOURCE_NOT_ALLOWED")
            scan_formats = tuple(sig.get("scan_formats", DEFAULT_SCAN))
            if ext not in sig.get("allowed_formats", []) and ext not in scan_formats:
                return self._block(sig, f"model format .{ext} is not allowed", "MODEL_FORMAT_NOT_ALLOWED")
        if ext in scan_formats:
            try:
                found = set(scan_pickle_bytes(data))
            except Exception as exc:
                return Verdict.block(self.id, f"artifact could not be scanned: {exc}", code="ARTIFACT_UNPARSEABLE",
                                     owasp=("LLM04:2026", "ASI04"))
            for sig in feed.by_type("pickle_opcode"):
                bad = found & set(sig.get("match", []))
                if bad:
                    return self._block(sig, f"pickle imports dangerous callables: {', '.join(sorted(bad))}",
                                       "MALICIOUS_PICKLE", opcodes=sorted(bad))
        return None

    def _urls(self, ctx, feed):
        for url in urls_in(ctx.response_text):
            host = host_of(url)
            for sig in feed.by_type("url_pattern"):
                if any(re.search(p, host) for p in sig.get("match", [])):
                    return self._block(sig, f"response links to known exfiltration host {host}", "EXFIL_URL", url=url)
        return None
