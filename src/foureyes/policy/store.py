from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

import yaml

from .catalog import CATALOG_IDS
from .snapshot import PolicySnapshot
from .validator import PolicyError


def diff_dicts(a: dict, b: dict, prefix: str = "") -> list[str]:
    out: list[str] = []
    for k in sorted(set(a) | set(b)):
        p = f"{prefix}{k}"
        if k not in a:
            out.append(f"+ {p}")
        elif k not in b:
            out.append(f"- {p}")
        elif isinstance(a[k], dict) and isinstance(b[k], dict):
            out += diff_dicts(a[k], b[k], p + ".")
        elif a[k] != b[k]:
            out.append(f"~ {p}: {a[k]!r} -> {b[k]!r}")
    return out


class PolicyStore:
    def __init__(self, path: Path, on_event: Callable[[dict], None] | None = None,
                 base_dir: Path | None = None):
        self.path = Path(path)
        self.base_dir = Path(base_dir) if base_dir else self.path.parent
        self._on_event = on_event or (lambda e: None)
        self._lock = threading.Lock()
        self._stamp: tuple[int, int] | None = None
        self.last_error: str | None = None
        self.history: list[dict] = []
        self._counter = 0
        self._snapshot = self._load(initial=True)

    def current(self) -> PolicySnapshot:
        return self._snapshot

    def _read(self) -> dict:
        try:
            raw = yaml.safe_load(self.path.read_text())
        except yaml.YAMLError as exc:
            raise PolicyError(f"yaml error: {exc}") from exc
        if raw is None:
            raise PolicyError("schema error: policy file is empty")
        return raw

    def _stat(self) -> tuple[int, int]:
        st = self.path.stat()
        return (st.st_mtime_ns, st.st_size)

    def _load(self, initial: bool = False) -> PolicySnapshot:
        raw = self._read()
        snap = PolicySnapshot.from_dict(raw, base_dir=self.base_dir, snap_id=self._counter + 1)
        self._counter += 1
        self._stamp = self._stat()
        if not initial:
            self._record_reload(self._snapshot, snap)
        else:
            self.history.append({"version": snap.label, "ts": time.time(), "event": "policy.loaded", "diff": [],
                                 "warnings": list(snap.warnings)})
        return snap

    def _record_reload(self, old: PolicySnapshot, new: PolicySnapshot) -> None:
        diff = diff_dicts(old.raw, new.raw)
        entry = {"version": new.label, "ts": time.time(), "event": "policy.reloaded", "diff": diff,
                 "warnings": list(new.warnings)}
        self.history.append(entry)
        self._on_event({"event": "policy.reloaded", "policy_version": new.label, "diff": diff,
                        "warnings": list(new.warnings)})
        for cid in CATALOG_IDS:
            if old.has_control(cid) and not new.has_control(cid):
                self._on_event({"event": "control.removed", "control": cid, "policy_version": new.label})
            if new.has_control(cid) and not old.has_control(cid):
                self._on_event({"event": "control.restored", "control": cid, "policy_version": new.label})

    def reload_if_changed(self) -> bool:
        with self._lock:
            try:
                stamp = self._stat()
            except OSError:
                return False
            if stamp == self._stamp:
                return False
            try:
                self._snapshot = self._load()
                self.last_error = None
                return True
            except PolicyError as exc:
                self._stamp = stamp  # do not re-report the same broken file
                self.last_error = str(exc)
                self.history.append({"version": self._snapshot.label, "ts": time.time(),
                                     "event": "policy.rejected", "diff": [], "error": str(exc)})
                self._on_event({"event": "policy.rejected", "reason": str(exc),
                                "policy_version": self._snapshot.label})
                return False
