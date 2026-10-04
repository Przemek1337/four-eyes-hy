import os
import time

import pytest
import yaml

from foureyes.policy.snapshot import PolicySnapshot
from foureyes.policy.store import PolicyStore
from foureyes.policy.validator import PolicyError
from helpers import ROOT, base_policy, policy_with, snapshot


def test_sample_policy_is_valid_and_exposes_accessors():
    s = snapshot()
    assert s.class_order == ["public", "personal_data", "bank_secret"]
    assert s.allowed_upstream_types("public") == ["local", "external"]
    assert s.allowed_upstream_types("bank_secret") == ["local"]
    assert s.source_for("mcp:entities_get")["class"] == "personal_data"
    assert s.source_for("mcp:unknown_tool")["class"] == "bank_secret"
    assert s.provider_type("external") == "external"
    assert s.default_local_model("kyc-agent") == "basal-1.0-1.5B"
    assert s.first_model_of_type("external") == "ext-gpt-sim"
    assert s.route_for("ext-gpt-sim", ["local", "external"]).type == "external"
    assert s.team_of("kyc-agent") == "compliance"


@pytest.mark.parametrize("mutate,msg", [
    (lambda r: r.update(bogus=1), "schema"),
    (lambda r: r["controls"].update({"made.up": {"mode": "enforce"}}), "unknown control"),
    (lambda r: r["controls"]["output.safe"].update(mode="sideways"), "mode"),
    (lambda r: r["controls"].pop("auth.agent_key"), "baseline"),
    (lambda r: r["controls"]["auth.agent_key"].update(mode="monitor"), "baseline"),
    (lambda r: r["data_classes"]["allowed_upstream_types"].update(bank_secret=["local", "external"]), "external"),
    (lambda r: r["data_classes"]["allowed_upstream_types"].update(public=["external"]), "local"),
    (lambda r: r["routing"].update(on_private_external_request="maybe"), "on_private_external_request"),
    (lambda r: r["sources"].update({"mcp:x": {"class": "nope"}}), "class"),
    (lambda r: r["agents"]["kyc-agent"].update(default_model="ghost"), "default_model"),
])
def test_invalid_policies_are_rejected(mutate, msg):
    raw = base_policy()
    mutate(raw)
    with pytest.raises(PolicyError) as e:
        PolicySnapshot.from_dict(raw, base_dir=ROOT)
    assert msg in str(e.value)


def _write(path, raw):
    path.write_text(yaml.safe_dump(raw))
    # make mtime strictly newer even on coarse filesystems
    t = time.time() + _write.n
    _write.n += 1
    os.utime(path, (t, t))


_write.n = 1


def test_hot_reload_and_rejection_keep_previous(tmp_path):
    p = tmp_path / "policy.yaml"
    _write(p, policy_with())
    events = []
    store = PolicyStore(p, on_event=events.append, base_dir=ROOT)
    assert store.current().label == "v1"

    _write(p, policy_with({"profile": "relaxed"}))
    assert store.reload_if_changed() is True
    assert store.current().label == "v2" and store.current().policy.profile == "relaxed"
    assert events[-1]["event"] == "policy.reloaded"
    assert any("profile" in d for d in events[-1]["diff"])

    p.write_text("")  # empty file
    os.utime(p, (time.time() + 50, time.time() + 50))
    assert store.reload_if_changed() is False
    assert store.current().label == "v2" and store.last_error
    assert events[-1]["event"] == "policy.rejected"

    p.write_text("- just\n- a list\n")
    os.utime(p, (time.time() + 60, time.time() + 60))
    store.reload_if_changed()
    assert store.current().label == "v2"


def test_removing_and_restoring_controls_emits_events(tmp_path):
    p = tmp_path / "policy.yaml"
    _write(p, policy_with())
    events = []
    store = PolicyStore(p, on_event=events.append, base_dir=ROOT)
    _write(p, policy_with(remove_controls=["log.redact"]))
    store.reload_if_changed()
    assert any(e["event"] == "control.removed" and e["control"] == "log.redact" for e in events)
    _write(p, policy_with())
    store.reload_if_changed()
    assert any(e["event"] == "control.restored" and e["control"] == "log.redact" for e in events)


def test_baseline_removal_via_file_is_rejected(tmp_path):
    p = tmp_path / "policy.yaml"
    _write(p, policy_with())
    store = PolicyStore(p, base_dir=ROOT)
    _write(p, policy_with(remove_controls=["auth.agent_key"]))
    assert store.reload_if_changed() is False
    assert "baseline control" in store.last_error
    assert store.current().has_control("auth.agent_key")


def test_initial_invalid_policy_raises(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text("version: [")
    with pytest.raises(PolicyError):
        PolicyStore(p, base_dir=ROOT)
