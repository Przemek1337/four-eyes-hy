import json
from types import SimpleNamespace

import pytest

from foureyes.controls.sem_judge import ActionJudgeControl
from foureyes.core.types import Outcome
from foureyes.semantic.decision_model_registry import DecisionModelRegistry
from foureyes.semantic.judge import MockJudge
from foureyes.semantic.mock_decision_client import MockDecisionClient
from helpers import make_ctx

OUT = (("external.example", "out_of_scope"),)


def tool_ctx(client, tool, args, overrides=None, task="KYC for Nordwind Sp. z o.o."):
    services = SimpleNamespace(decision_models=DecisionModelRegistry(override=client), judge=MockJudge(fail=True))
    ctx = make_ctx(kind="tool", tool=tool, args=args, overrides=overrides, services=services)
    ctx.session.task = task
    return ctx


def run(ctx):
    return ActionJudgeControl(ctx.policy.control_cfg("sem.action_judge")).evaluate(ctx, "pre")


def test_internal_email_is_not_judged():
    client = MockDecisionClient(choice_rules=OUT)
    assert run(tool_ctx(client, "send_email", {"to": "kyc@bank.internal"})) is None
    assert client.calls == []


@pytest.mark.positive
def test_consistent_critical_action_is_allowed_with_the_ai_detail():
    v = run(tool_ctx(MockDecisionClient(choice_rules=OUT), "entities_submit", {"entity_id": "E1"}))
    assert v.outcome is Outcome.ALLOW and v.detail["ai"]["model"] == "basal" and v.detail["judge"]["consistent"]


@pytest.mark.negative
@pytest.mark.owasp("LLM01:2026")
def test_out_of_scope_email_goes_to_a_human():
    v = run(tool_ctx(MockDecisionClient(choice_rules=OUT), "send_email", {"to": "kyc-verify@external.example"}))
    assert v.outcome is Outcome.APPROVAL and v.code == "ACTION_INCONSISTENT" and v.layer == "ai"
    assert v.detail["judge"]["score"] == pytest.approx(0.95) and v.detail["ai"]["rule"] == "out_of_scope"


def test_unconfident_answer_follows_on_error():
    unsure = MockDecisionClient(choice_result=("consistent", 0.6))
    v = run(tool_ctx(unsure, "entities_submit", {"entity_id": "E1"}))
    assert v.outcome is Outcome.APPROVAL and v.code == "JUDGE_UNCERTAIN" and v.detail["ai"]["uncertain"] is True
    strict = tool_ctx(unsure, "entities_submit", {"entity_id": "E1"},
                      overrides={"controls": {"sem.action_judge": {"on_error": "block"}}})
    assert run(strict).outcome is Outcome.BLOCK


def test_the_model_sees_task_tool_args_and_labels_but_never_documents():
    client = MockDecisionClient()
    ctx = tool_ctx(client, "entities_submit", {"entity_id": "E1"})
    ctx.request.messages = [{"role": "tool", "content": "HIDDEN DOCUMENT TEXT"}]
    ctx.session.labels.add("untrusted")
    run(ctx)
    state = json.loads(client.calls[0][1])
    assert state == {"args": {"entity_id": "E1"}, "labels": ["untrusted"], "task": "KYC for Nordwind Sp. z o.o.",
                     "tool": "entities_submit"}
    assert "HIDDEN DOCUMENT TEXT" not in client.calls[0][1]


@pytest.mark.negative
def test_model_failure_goes_to_approval():
    v = run(tool_ctx(MockDecisionClient(fail=True), "send_email", {"to": "x@external.example"}))
    assert v.outcome is Outcome.APPROVAL and v.code == "JUDGE_UNAVAILABLE"


def test_non_critical_tools_are_not_judged():
    client = MockDecisionClient()
    assert run(tool_ctx(client, "entities_get", {"client_id": "C1"})) is None and client.calls == []


def test_without_a_registry_the_legacy_judge_is_used():
    ctx = make_ctx(kind="tool", tool="send_email", args={"to": "e@evil.example"},
                   services=SimpleNamespace(judge=MockJudge()))
    ctx.session.task = "KYC"
    v = run(ctx)
    assert v.outcome is Outcome.APPROVAL and "ai" not in v.detail


@pytest.mark.negative
@pytest.mark.parametrize("choice, expected", [("out_of_scope", Outcome.APPROVAL), ("consistent", Outcome.ALLOW)])
def test_basal_answer_without_probabilities_scores_from_the_choice(choice, expected):
    # review I1: Basal answered a confident out_of_scope with no probabilities map and the action was allowed
    import httpx
    from foureyes.semantic.basal_decision_client import BasalDecisionClient

    answer = {"answers": {"q": {"type": "choice", "choice": choice, "confidence": 0.97}}}
    basal = BasalDecisionClient("http://basal:8000", "basal-1.0-4.5B", client=httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=answer))))
    v = run(tool_ctx(basal, "send_email", {"to": "kyc-verify@external.example"}))
    if expected is Outcome.APPROVAL:
        assert v.outcome is Outcome.APPROVAL and v.code == "ACTION_INCONSISTENT"
        assert v.detail["judge"]["score"] == pytest.approx(0.97)
    else:
        assert v.outcome is Outcome.ALLOW and v.detail["judge"]["score"] == pytest.approx(0.03)
