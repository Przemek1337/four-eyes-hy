from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Callable


@dataclass
class Approval:
    id: str
    hash: str
    session_id: str
    agent_id: str
    tool: str
    args: dict
    rule: str
    reason: str
    labels: list[str]
    data_class: str
    judge: dict | None
    supplied_reason: str | None
    created: float
    expires_at: float
    status: str = "pending"  # pending | approved | denied | consumed
    decided_by: str | None = None
    decided_at: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Redeem:
    code: str
    approval: Approval | None = None


class ApprovalService:
    def __init__(self, ttl_seconds: int = 900, clock: Callable[[], float] = time.time):
        self.ttl = ttl_seconds
        self.clock = clock
        self._items: dict[str, Approval] = {}
        self._lock = threading.Lock()

    @staticmethod
    def params_hash(tool: str, args: dict) -> str:
        canonical = json.dumps({"tool": tool, "args": args}, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def request(self, session_id, agent_id, tool, args, rule, reason, labels, data_class,
                judge=None, supplied_reason=None) -> Approval:
        h = self.params_hash(tool, args)
        with self._lock:
            for a in self._items.values():
                if a.status == "pending" and (a.session_id, a.agent_id, a.hash) == (session_id, agent_id, h) \
                        and a.expires_at > self.clock():
                    return a
            now = self.clock()
            a = Approval(id=uuid.uuid4().hex[:10], hash=h, session_id=session_id, agent_id=agent_id,
                         tool=tool, args=args, rule=rule, reason=reason, labels=sorted(labels),
                         data_class=data_class, judge=judge, supplied_reason=supplied_reason,
                         created=now, expires_at=now + self.ttl)
            self._items[a.id] = a
            return a

    def decide(self, approval_id: str, approve: bool, by: str = "compliance") -> Approval:
        with self._lock:
            a = self._items[approval_id]
            if a.status != "pending":
                return a
            a.status = "approved" if approve else "denied"
            a.decided_by, a.decided_at = by, self.clock()
            return a

    def redeem(self, approval_id, session_id, agent_id, tool, args) -> Redeem:
        with self._lock:
            a = self._items.get(approval_id)
            if a is None:
                return Redeem("APPROVAL_UNKNOWN")
            if (a.session_id, a.agent_id) != (session_id, agent_id) or a.hash != self.params_hash(tool, args):
                return Redeem("APPROVAL_MISMATCH", a)
            if a.status == "consumed":
                return Redeem("APPROVAL_REUSED", a)
            if a.expires_at <= self.clock():
                return Redeem("APPROVAL_EXPIRED", a)
            if a.status == "denied":
                return Redeem("APPROVAL_DENIED", a)
            if a.status == "pending":
                return Redeem("pending", a)
            a.status = "consumed"
            return Redeem("ok", a)

    def pending(self) -> list[Approval]:
        with self._lock:
            return [a for a in self._items.values() if a.status == "pending" and a.expires_at > self.clock()]

    def all(self) -> list[Approval]:
        with self._lock:
            return sorted(self._items.values(), key=lambda a: a.created, reverse=True)

    def get(self, approval_id: str) -> Approval | None:
        return self._items.get(approval_id)
