import pytest
import yaml

from foureyes.policy.store import PolicyStore
from foureyes.policy.validator import PolicyError
from foureyes.semantic.decision_model_types import model_refs
from helpers import policy_with, snapshot


def test_shipped_policy_names_granite_for_injection_and_basal_for_the_rest():
    snap = snapshot()
    assert model_refs(snap.controls) == {"data.classify_net": "basal", "sem.prompt_injection": "granite_guardian",
                                         "sem.action_judge": "basal"}
    assert snap.decision_model_cfg("granite_guardian")["location"] == "local"
    assert snap.decision_model_cfg("mock")["type"] == "mock"
    assert snap.decision_model_cfg("jev")["location"] == "external"
    assert snap.warnings == []


@pytest.mark.negative
def test_external_model_in_a_content_control_is_rejected():
    with pytest.raises(PolicyError, match="external"):
        snapshot({"controls": {"sem.action_judge": {"model": "jev"}}})


def test_unknown_model_and_missing_capability_are_rejected():
    with pytest.raises(PolicyError, match="unknown decision model"):
        snapshot({"controls": {"sem.prompt_injection": {"model": "gpt-judge"}}})
    with pytest.raises(PolicyError, match="choice"):
        snapshot({"controls": {"sem.action_judge": {"model": "granite_guardian"}}})
    with pytest.raises(PolicyError, match="unknown decision model type"):
        snapshot({"decision_models": {"x": {"type": "magic", "location": "local"}}})


def test_rules_options_and_classes_must_be_complete():
    # helpers.deep_merge merges nested dicts, so a key is emptied by setting it to None
    with pytest.raises(PolicyError, match="rules"):
        snapshot({"controls": {"sem.prompt_injection": {"rules": None}}})
    with pytest.raises(PolicyError, match="out_of_scope"):
        snapshot({"controls": {"sem.action_judge": {"options": None}}})
    with pytest.raises(PolicyError, match="unknown data class"):
        snapshot({"controls": {"data.classify_net": {"ai": {"classes": {"secret_sauce": "x"}}}}})


def test_legacy_names_are_still_accepted():
    snap = snapshot({"controls": {"sem.prompt_injection": {"model": "promptguard"},
                                  "sem.action_judge": {"model": "ollama"}}})
    assert model_refs(snap.controls)["sem.prompt_injection"] == "promptguard"


def test_builtin_rule_on_basal_is_a_warning_not_an_error():
    snap = snapshot({"controls": {"sem.prompt_injection": {"model": "basal"}}})
    assert snap.warnings == ["rule.skipped: sem.prompt_injection rule 'jailbreak' is not built into basal"]


def test_reload_event_carries_the_warnings(tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(policy_with()))
    events = []
    store = PolicyStore(path, on_event=events.append, base_dir=tmp_path)
    raw = policy_with({"controls": {"sem.prompt_injection": {"model": "basal"}}})
    path.write_text(yaml.safe_dump(raw) + "\n# changed\n")
    assert store.reload_if_changed() is True
    reloaded = next(e for e in events if e["event"] == "policy.reloaded")
    assert reloaded["warnings"] and "jailbreak" in reloaded["warnings"][0]
    assert store.history[-1]["warnings"] == reloaded["warnings"]
