from __future__ import annotations

import json
import threading
import time
from pathlib import Path

KNOWN_TYPES = {"pickle_opcode", "file_hash", "model_source", "tool_arg_pattern", "prompt_pattern",
               "unicode_smuggling", "url_pattern"}


class FeedStore:
    """Externally managed signature feed. A broken update never replaces a good feed."""

    def __init__(self, path: Path | str | None):
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self._sigs: list[dict] = []
        self.version: str | None = None
        self.last_reload: float | None = None
        self.error: str | None = None
        self._stamp: tuple[int, int] | None = None
        self.refresh_if_changed()

    def _validate(self, data) -> list[dict]:
        if not isinstance(data, dict) or not isinstance(data.get("signatures"), list) or "feed_version" not in data:
            raise ValueError("feed must be an object with feed_version and signatures")
        for sig in data["signatures"]:
            if not isinstance(sig, dict) or not {"id", "type", "action"} <= set(sig):
                raise ValueError(f"signature missing id/type/action: {sig!r}")
            if sig["type"] not in KNOWN_TYPES:
                raise ValueError(f"unknown signature type {sig['type']!r}")
        return data["signatures"]

    def refresh_if_changed(self) -> None:
        if self.path is None:
            return
        with self._lock:
            try:
                st = self.path.stat()
            except OSError as exc:
                self.error = f"feed unreadable: {exc}"
                return
            stamp = (st.st_mtime_ns, st.st_size)
            if stamp == self._stamp:
                return
            self._stamp = stamp
            try:
                data = json.loads(self.path.read_text())
                self._sigs = self._validate(data)
                self.version = str(data["feed_version"])
                self.last_reload = time.time()
                self.error = None
            except (ValueError, json.JSONDecodeError) as exc:
                self.error = f"feed rejected: {exc}"

    def by_type(self, sig_type: str) -> list[dict]:
        return [s for s in self._sigs if s["type"] == sig_type]

    def status(self) -> dict:
        return {"version": self.version, "count": len(self._sigs), "last_reload": self.last_reload,
                "error": self.error, "source": str(self.path) if self.path else None}
