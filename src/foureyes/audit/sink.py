from __future__ import annotations

import csv
import io
import json
import queue
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from foureyes.detect.patterns import redact_obj

DEFAULT_DETECTORS = ["secrets", "iban", "pesel", "passport"]


class AuditSink:
    COLUMNS = ["decision_id", "ts", "session_id", "agent", "action", "resource", "decision", "rule",
               "reason", "layer", "labels", "owasp", "policy_version", "signature_id", "latency_ms",
               "upstream", "upstream_type", "data_class", "provider", "tokens", "cost_usd", "compute_s"]

    def __init__(self, path: Path, snapshot_provider: Callable, max_memory: int = 5000):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._snapshot = snapshot_provider
        self._events: deque[dict] = deque(maxlen=max_memory)
        self._lock = threading.Lock()
        self._subs: list[queue.Queue] = []

    def _redaction(self) -> tuple[str, list[str]]:
        snap = self._snapshot()
        cfg = snap.control_cfg("log.redact")
        detectors = snap.policy.log_redaction.get("detectors", DEFAULT_DETECTORS)
        if cfg is None:
            return "off", detectors
        return ("monitor" if cfg.get("mode") == "monitor" else "on"), detectors

    def emit(self, event: dict) -> dict:
        snap = self._snapshot()
        state, detectors = self._redaction()
        ev = dict(event)
        ev.setdefault("event", "decision")
        ev.setdefault("decision_id", uuid.uuid4().hex[:12])
        ev["ts"] = datetime.now(timezone.utc).isoformat()
        ev.setdefault("policy_version", snap.label)
        if state == "on":
            ev, _ = redact_obj(ev, detectors)
        ev["redaction"] = state
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
            self._events.append(ev)
            subs = list(self._subs)
        for q in subs:
            q.put(ev)
        return ev

    @staticmethod
    def _match(ev: dict, f: dict) -> bool:
        if f.get("event") and ev.get("event") != f["event"]:
            return False
        for key in ("agent", "decision", "rule", "data_class"):
            if f.get(key) and ev.get(key) != f[key]:
                return False
        if f.get("session") and ev.get("session_id") != f["session"]:
            return False
        if f.get("owasp") and f["owasp"] not in (ev.get("owasp") or []):
            return False
        if f.get("from_ts") and ev.get("ts", "") < f["from_ts"]:
            return False
        if f.get("to_ts") and ev.get("ts", "") > f["to_ts"]:
            return False
        return True

    def events(self, **filters) -> list[dict]:
        with self._lock:
            snapshot = list(self._events)
        return [e for e in snapshot if self._match(e, filters)]

    def export(self, fmt: str, **filters) -> str:
        rows = [e for e in self.events(**filters) if e.get("event", "decision") == "decision"] \
            if fmt == "csv" else self.events(**filters)
        if fmt == "jsonl":
            return "".join(json.dumps(e, ensure_ascii=False, default=str) + "\n" for e in rows)
        if fmt == "csv":
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=self.COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for e in rows:
                writer.writerow({c: ";".join(map(str, e.get(c)))
                                 if isinstance(e.get(c), (list, tuple)) else e.get(c, "")
                                 for c in self.COLUMNS})
            return buf.getvalue()
        raise ValueError(f"unknown export format {fmt!r}")

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subs:
                self._subs.remove(q)
