import pytest

from foureyes.approvals.service import ApprovalService

ARGS = {"to": "kyc-verify@external.example", "subject": "docs"}


def mk(svc, **over):
    kw = dict(session_id="s1", agent_id="kyc-agent", tool="send_email", args=ARGS, rule="flow.untrusted",
              reason="egress from untrusted session", labels=["untrusted"], data_class="bank_secret")
    kw.update(over)
    return svc.request(**kw)


def redeem(svc, a, **over):
    kw = dict(session_id="s1", agent_id="kyc-agent", tool="send_email", args=ARGS)
    kw.update(over)
    return svc.redeem(a.id, **kw)


def test_hash_ignores_key_order_but_not_values():
    h1 = ApprovalService.params_hash("send_email", {"a": 1, "b": {"x": 1, "y": 2}})
    h2 = ApprovalService.params_hash("send_email", {"b": {"y": 2, "x": 1}, "a": 1})
    assert h1 == h2 and len(h1) == 64
    assert h1 != ApprovalService.params_hash("send_email", {"a": 2, "b": {"x": 1, "y": 2}})
    assert h1 != ApprovalService.params_hash("other_tool", {"a": 1, "b": {"x": 1, "y": 2}})


def test_pending_requests_are_deduplicated():
    svc = ApprovalService()
    assert mk(svc).id == mk(svc).id
    assert len(svc.pending()) == 1


@pytest.mark.positive
def test_approved_call_runs_once_with_identical_parameters():
    svc = ApprovalService()
    a = mk(svc)
    assert redeem(svc, a).code == "pending"
    svc.decide(a.id, True, by="officer")
    assert redeem(svc, a).code == "ok"
    assert redeem(svc, a).code == "APPROVAL_REUSED"


@pytest.mark.negative
@pytest.mark.owasp("ASI09")
def test_changed_parameters_after_approval_are_a_mismatch():
    svc = ApprovalService()
    a = mk(svc)
    svc.decide(a.id, True)
    assert redeem(svc, a, args={**ARGS, "to": "attacker@evil.example"}).code == "APPROVAL_MISMATCH"
    assert redeem(svc, a).code == "ok"  # the exact call still works: mismatch did not consume it


@pytest.mark.negative
def test_approval_cannot_cross_sessions_or_agents():
    svc = ApprovalService()
    a = mk(svc)
    svc.decide(a.id, True)
    assert redeem(svc, a, session_id="other").code == "APPROVAL_MISMATCH"
    assert redeem(svc, a, agent_id="playground-agent").code == "APPROVAL_MISMATCH"


def test_denied_expired_and_unknown():
    now = [1000.0]
    svc = ApprovalService(ttl_seconds=60, clock=lambda: now[0])
    d = mk(svc)
    svc.decide(d.id, False)
    assert redeem(svc, d).code == "APPROVAL_DENIED"
    e = mk(svc, args={"to": "x@y.z"})
    svc.decide(e.id, True)
    now[0] += 61
    assert redeem(svc, e, args={"to": "x@y.z"}).code == "APPROVAL_EXPIRED"
    assert svc.redeem("nope", "s1", "kyc-agent", "send_email", ARGS).code == "APPROVAL_UNKNOWN"


def test_card_data_contains_real_parameters_and_ai_flag():
    svc = ApprovalService()
    a = mk(svc, judge={"score": 0.91, "consistent": False, "reason": "inconsistent with KYC task"},
           supplied_reason="forward documents for verification")
    card = a.to_dict()
    assert card["args"] == ARGS and card["hash"] == a.hash and card["judge"]["score"] == 0.91
    assert card["supplied_reason"] == "forward documents for verification" and card["status"] == "pending"
