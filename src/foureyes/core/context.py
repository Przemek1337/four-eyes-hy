from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from .session import SessionState
from .types import Request, Route, Verdict


@dataclass
class Services:
    policy_store: Any = None
    sessions: Any = None
    meter: Any = None
    approvals: Any = None
    audit: Any = None
    telemetry: Any = None
    feed: Any = None
    upstreams: Any = None
    router: Any = None
    anonymizer: Any = None
    injection: Any = None
    judge: Any = None
    document_runner: Any = None


@dataclass
class Ctx:
    request: Request
    policy: Any  # PolicySnapshot
    session: SessionState
    services: Any
    decision_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    route: Route | None = None
    verdicts: list[Verdict] = field(default_factory=list)
    monitor: list[Verdict] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)
    spans: list[dict] = field(default_factory=list)
    notes: dict = field(default_factory=dict)
    response_text: str | None = None
    result: Any = None
    usage: dict = field(default_factory=dict)
    upstream_seconds: float = 0.0
    source: str | None = None
    source_labels: list[str] = field(default_factory=list)

    def agent_cfg(self) -> dict:
        return self.policy.agents.get(self.request.agent_id or "", {})

    def overrides(self, control_id: str) -> dict:
        return (self.agent_cfg().get("overrides") or {}).get(control_id, {})

    def profile(self) -> str:
        return self.agent_cfg().get("profile") or self.policy.policy.profile

    def alert(self, kind: str, **data) -> None:
        self.alerts.append({"kind": kind, **data})
