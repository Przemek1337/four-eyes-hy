import httpx

from foureyes.posture import compute
from foureyes.semantic.basal_decision_client import BasalDecisionClient
from foureyes.semantic.decision_model_registry import DecisionModelRegistry
from foureyes.semantic.granite_guardian_decision_client import GraniteGuardianDecisionClient
from foureyes.semantic.mock_decision_client import MockDecisionClient
from helpers import make_gateway, snapshot

OK_FEED = {"version": "1", "error": None}


def test_registry_builds_clients_from_the_policy_and_caches_them():
    reg = DecisionModelRegistry()
    snap = snapshot()
    g = reg.client("granite_guardian", snap)
    assert isinstance(g, GraniteGuardianDecisionClient) and reg.client("granite_guardian", snap) is g
    assert isinstance(reg.client("basal", snap), BasalDecisionClient)
    assert isinstance(reg.client("mock", snap), MockDecisionClient)


def test_changed_config_builds_a_new_client():
    reg = DecisionModelRegistry()
    a = reg.client("basal", snapshot())
    b = reg.client("basal", snapshot({"decision_models": {"basal": {"base_url": "http://other:9000"}}}))
    assert a is not b and b.base_url == "http://other:9000"


def test_override_answers_for_every_name():
    mock = MockDecisionClient()
    reg = DecisionModelRegistry(override=mock)
    assert reg.client("granite_guardian", snapshot()) is mock and reg.client("basal", snapshot()) is mock


def test_health_covers_models_used_by_active_controls_only():
    down = MockDecisionClient(fail=True)
    up = MockDecisionClient()
    reg = DecisionModelRegistry(factories={"granite_guardian": lambda cfg: down, "basal": lambda cfg: up,
                                           "mock": lambda cfg: up})
    assert reg.health(snapshot()) == {"granite_guardian": False, "basal": True}
    only_judge = snapshot(remove_controls=["sem.prompt_injection", "data.classify_net"])
    assert reg.health(only_judge) == {"basal": True}
    legacy = snapshot({"controls": {"sem.prompt_injection": {"model": "promptguard"}}})
    assert "promptguard" not in reg.health(legacy)


def test_posture_penalises_each_down_model():
    snap = snapshot()
    one = compute(snap, ai_healthy=True, feed_status=OK_FEED, tests=None, ai_models_down=["granite_guardian"])
    two = compute(snap, ai_healthy=True, feed_status=OK_FEED, tests=None, ai_models_down=["granite_guardian", "basal"])
    assert one["score"] == 90 and two["score"] == 80
    assert any(b["item"] == "AI model granite_guardian" for b in two["breakdown"])


def test_admin_posture_reports_a_down_model(tmp_path):
    reg = DecisionModelRegistry(factories={"granite_guardian": lambda cfg: MockDecisionClient(fail=True),
                                           "basal": lambda cfg: MockDecisionClient(),
                                           "mock": lambda cfg: MockDecisionClient()})
    gw = make_gateway(tmp_path, decision_models=reg)
    body = gw.client.get("/admin/posture").json()
    assert any(b["item"] == "AI model granite_guardian" for b in body["breakdown"])
