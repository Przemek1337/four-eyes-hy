from __future__ import annotations

from pathlib import Path

from foureyes.approvals.service import ApprovalService
from foureyes.audit.sink import AuditSink
from foureyes.budgets.meter import MeterStore
from foureyes.core.context import Services
from foureyes.core.session import SessionStore
from foureyes.core.telemetry import Telemetry
from foureyes.policy.store import PolicyStore
from foureyes.routing.anonymizer import NoOpAnonymizer
from foureyes.routing.router import RuleBasedRouter
from foureyes.semantic.injection import MockInjectionScorer
from foureyes.semantic.judge import MockJudge
from foureyes.signatures.feed import FeedStore
from foureyes.upstream.base import UpstreamRegistry
from foureyes.upstream.mock import MockModelUpstream


def build_services(policy_path, *, audit_path, meter_path: str = ":memory:", upstreams=None, injection=None,
                   judge=None, router=None, base_dir=None, decision_models=None) -> Services:
    policy_path = Path(policy_path)
    holder: dict = {}
    store = PolicyStore(policy_path, on_event=lambda e: holder["audit"].emit(e), base_dir=base_dir)
    audit = AuditSink(Path(audit_path), store.current)
    holder["audit"] = audit
    source = store.current().policy.signatures.get("source")
    feed = FeedStore(store.base_dir / source if source else None)
    upstreams = upstreams or UpstreamRegistry(
        {"local": MockModelUpstream("local"), "external": MockModelUpstream("external")}, None)
    return Services(policy_store=store, sessions=SessionStore(), meter=MeterStore(meter_path),
                    approvals=ApprovalService(), audit=audit, telemetry=Telemetry(), feed=feed,
                    upstreams=upstreams, router=router or RuleBasedRouter(), anonymizer=NoOpAnonymizer(),
                    injection=injection or MockInjectionScorer(), judge=judge or MockJudge(), decision_models=decision_models)
