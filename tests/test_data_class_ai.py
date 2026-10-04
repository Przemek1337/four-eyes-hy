from types import SimpleNamespace

import pytest

from foureyes.controls.classify import ClassifyNetControl
from foureyes.core.types import Outcome
from foureyes.semantic.decision_model_registry import DecisionModelRegistry
from foureyes.semantic.mock_decision_client import MockDecisionClient
from helpers import chat, make_ctx, make_gateway

SECRET = "Klient Nordwind ma przyznany limit 2 mln zł, wewnętrzny rating B-, trwa restrukturyzacja."
RULES = (("rating", "bank_secret"),)


def ctx_for(text, client, session_class="public", overrides=None):
    services = SimpleNamespace(decision_models=DecisionModelRegistry(override=client))
    return make_ctx(services=services, session_class=session_class, overrides=overrides,
                    messages=[{"role": "user", "content": text}])


def run(ctx):
    return ClassifyNetControl(ctx.policy.control_cfg("data.classify_net")).evaluate(ctx, "pre")


@pytest.mark.negative
@pytest.mark.owasp("LLM02:2026")
def test_bank_secret_without_pesel_or_iban_is_raised_by_the_ai():
    ctx = ctx_for(SECRET, MockDecisionClient(choice_rules=RULES))
    v = run(ctx)
    assert v.outcome is Outcome.ALLOW and v.layer == "ai" and v.detail["ai"]["rule"] == "bank_secret"
    assert ctx.session.data_class == "bank_secret"
    raised = [e for e in ctx.session.drain_events() if e["event"] == "class.raised"]
    assert raised[-1]["source"] == "ai:basal"


def test_uncertain_answer_takes_the_highest_class():
    ctx = ctx_for("hmm", MockDecisionClient(choice_result=("public", 0.5)))
    run(ctx)
    assert ctx.session.data_class == "bank_secret" and ctx.notes["ai"]["data.classify_net"]["uncertain"] is True


@pytest.mark.positive
def test_class_never_drops_and_public_text_changes_nothing():
    ctx = ctx_for("What documents do I need?", MockDecisionClient(), session_class="personal_data")
    assert run(ctx) is None and ctx.session.data_class == "personal_data"


def test_no_question_at_the_top_class_or_for_empty_text():
    top = MockDecisionClient()
    run(ctx_for(SECRET, top, session_class="bank_secret"))
    empty = MockDecisionClient()
    run(ctx_for("   ", empty))
    assert top.calls == [] and empty.calls == []


@pytest.mark.negative
def test_failure_raises_the_session_to_the_highest_class():
    ctx = ctx_for("hello", MockDecisionClient(fail=True))
    v = run(ctx)
    assert v.code == "CLASSIFIER_UNAVAILABLE" and ctx.session.data_class == "bank_secret"


def test_deterministic_block_still_wins_and_skips_the_model():
    client = MockDecisionClient(choice_rules=RULES)
    ctx = ctx_for("PESEL 44051401359", client, overrides={"dlp": {"pii_in_prompt": {"on_detect": "block"}}})
    assert run(ctx).code == "PII_BLOCKED" and client.calls == []


def test_monitor_only_suggests_without_raising():
    ctx = ctx_for(SECRET, MockDecisionClient(choice_rules=RULES),
                  overrides={"controls": {"data.classify_net": {"mode": "monitor"}}})
    run(ctx)
    assert ctx.session.data_class == "public" and any(a["kind"] == "class.suggested" for a in ctx.alerts)


def test_without_a_registry_only_the_deterministic_net_runs():
    ctx = make_ctx(services=SimpleNamespace(), messages=[{"role": "user", "content": SECRET}])
    assert run(ctx) is None and ctx.session.data_class == "public"


@pytest.mark.negative
@pytest.mark.owasp("LLM02:2026")
def test_bank_secret_text_cannot_reach_an_external_model(tmp_path):
    gw = make_gateway(tmp_path, decision_models=DecisionModelRegistry(override=MockDecisionClient(choice_rules=RULES)))
    r = chat(gw, SECRET, session="x1", model="ext-gpt-sim")
    assert r.json()["error"]["code"] == "PRIVATE_DATA_EXTERNAL_MODEL"
