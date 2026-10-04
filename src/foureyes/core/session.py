from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class SessionState:
    session_id: str
    agent_id: str
    data_class: str
    created: float = field(default_factory=time.time)
    labels: set[str] = field(default_factory=set)
    scope: dict[str, str] = field(default_factory=dict)
    sensitive_terms: list[str] = field(default_factory=list)
    task: str | None = None
    steps: int = 0
    tokens: int = 0
    tools_called: list[str] = field(default_factory=list)
    last_turn: list[dict] = field(default_factory=list)  # Playground: the previous exchange, as the gateway delivered it
    _pending: list[dict] = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def raise_class(self, new: str, order: list[str], reason: str, source: str) -> bool:
        if new not in order:
            raise ValueError(f"unknown data class {new!r}")
        with self._lock:
            if order.index(new) <= order.index(self.data_class):
                return False
            self._pending.append({"event": "class.raised", "session_id": self.session_id,
                                  "from": self.data_class, "to": new, "reason": reason, "source": source})
            self.data_class = new
            return True

    def add_label(self, label: str, reason: str) -> bool:
        with self._lock:
            if label in self.labels:
                return False
            self.labels.add(label)
            self._pending.append({"event": "label.added", "session_id": self.session_id,
                                  "label": label, "reason": reason})
            return True

    def drain_events(self) -> list[dict]:
        with self._lock:
            events, self._pending = self._pending, []
            return events

    def bump_steps(self) -> int:
        with self._lock:
            self.steps += 1
            return self.steps

    def add_tokens(self, n: int) -> None:
        with self._lock:
            self.tokens += n

    def note_tool(self, tool: str) -> None:
        with self._lock:
            self.tools_called.append(tool)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.RLock()

    def get_or_create(self, session_id: str, agent_id: str, initial_class: str) -> SessionState:
        with self._lock:
            s = self._sessions.get(session_id)
            if s is None:
                s = SessionState(session_id=session_id, agent_id=agent_id, data_class=initial_class)
                self._sessions[session_id] = s
            return s

    def get(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def all(self) -> list[SessionState]:
        with self._lock:
            return list(self._sessions.values())
