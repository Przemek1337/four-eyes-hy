import pytest

from foureyes.semantic.decision_model_registry import DecisionModelRegistry
from foureyes.semantic.mock_decision_client import MockDecisionClient
from harness.demo_documents.calibrate_borderline_note import CANDIDATES, calibrate
from harness.demo_scenarios.demo_environment import DemoEnvironment, ScenarioResult
from harness.demo_scenarios.run_all_demo_scenarios import format_table, run_all
from harness.kyc.mock_decision_rules import BORDERLINE_NOTE_PREFIX, MOCK_DECISION_RULES
from helpers import kyc_gateway, snapshot

NAMES = ["clean_registry_extract", "injected_registry_extract", "borderline_registry_extract", "uk_registry_extract",
         "developer_without_access"]


def demo_env(tmp_path, monkeypatch, profile):
    monkeypatch.setenv("ANETA_DEV_CLI_KEY", "k-dev")
    gw = kyc_gateway(tmp_path, overrides={"profile": profile},
                     decision_models=DecisionModelRegistry(override=MockDecisionClient(**MOCK_DECISION_RULES)))
    return DemoEnvironment(gateway=gw.client, kyc_key="k-kyc", dev_key="k-dev")


@pytest.mark.parametrize("profile", ["strict", "relaxed"])
def test_every_demo_scenario_passes_on_mocks(tmp_path, monkeypatch, profile):
    results = run_all(demo_env(tmp_path, monkeypatch, profile))
    assert [r.name for r in results] == NAMES
    assert all(r.ok for r in results), format_table(results)


def test_a_failed_expectation_is_reported():
    bad = ScenarioResult("x").check("status", "complete", "blocked")
    assert not bad.ok and "FAIL" in format_table([bad]) and "expected 'complete'" in format_table([bad])


def test_calibration_picks_the_first_note_in_the_uncertainty_band():
    conf = snapshot().control_cfg("sem.prompt_injection")
    found = calibrate(MockDecisionClient(uncertain_patterns=("relationship manager",)), "granite_guardian", conf)
    assert found["note"] == CANDIDATES[1] and found["calibrated_with"] == "granite_guardian"
    assert calibrate(MockDecisionClient(), "granite_guardian", conf) is None
    assert all(c.lower().startswith(BORDERLINE_NOTE_PREFIX) for c in CANDIDATES)
