import json

from foureyes.semantic.decision_model_registry import DecisionModelRegistry
from foureyes.semantic.mock_decision_client import MockDecisionClient
from harness.demo_documents import DEMO_DOCUMENTS_DIR
from harness.demo_scenarios.evaluate_decision_models import evaluate
from harness.kyc.mock_decision_rules import MOCK_DECISION_RULES
from helpers import snapshot

ITEMS = json.loads((DEMO_DOCUMENTS_DIR / "eval_set.json").read_text(encoding="utf-8"))


def test_default_evaluation_uses_only_the_active_mvp_model():
    reg = DecisionModelRegistry(factories={
        "basal": lambda cfg: MockDecisionClient(**MOCK_DECISION_RULES),
        "granite_guardian": lambda cfg: (_ for _ in ()).throw(AssertionError("unused model contacted")),
    })
    report = evaluate(reg, snapshot(), ITEMS)
    assert set(report) == {"basal"}
    assert set(report["basal"]) == {"injection", "data_class", "action"}


def test_each_model_is_evaluated_only_on_checks_it_can_answer():
    reg = DecisionModelRegistry(override=MockDecisionClient(**MOCK_DECISION_RULES))
    report = evaluate(reg, snapshot(), ITEMS, model_names=["granite_guardian", "basal"])
    assert set(report["granite_guardian"]) == {"injection"}
    assert set(report["basal"]) == {"injection", "data_class", "action"}
    inj = report["granite_guardian"]["injection"]
    assert inj["n"] == 8 and 0 <= inj["accuracy"] <= 1 and set(inj["by_lang"]) == {"en", "pl"}
    assert {"p50_ms", "p95_ms", "uncertain", "items"} <= set(inj)
    hidden = next(i for i in inj["items"] if i["id"] == "inj-en-hidden")
    assert hidden["predicted"] == "yes"


def test_a_failing_model_is_reported_not_raised():
    reg = DecisionModelRegistry(override=MockDecisionClient(fail=True))
    report = evaluate(reg, snapshot(), ITEMS, model_names=["basal"])
    assert report["basal"]["action"]["accuracy"] == 0.0
    assert report["basal"]["action"]["items"][0]["predicted"].startswith("error:")
