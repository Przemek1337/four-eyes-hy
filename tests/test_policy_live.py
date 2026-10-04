import itertools
import os
import time

import pytest
import yaml

from helpers import DOC, call, chat, default_tools, make_gateway, policy_with

_tick = itertools.count(5, 5)


def rewrite(gw, overrides=None, remove_controls=()):
    gw.policy_path.write_text(yaml.safe_dump(policy_with(overrides, remove_controls)))
    t = time.time() + next(_tick)
    os.utime(gw.policy_path, (t, t))


def tools():
    t = default_tools()
    t.handlers["entities_documents_read"] = lambda client_id, document_id="clean": {
        "text": DOC if document_id == "poisoned" else "Plain articles of association."}
    return t


def submit_after_screening(gw, session, document_id):
    call(gw, "entities_documents_read", {"client_id": "C1", "document_id": document_id}, session)
    call(gw, "sanctions_check", {"name": "Nordwind"}, session)
    return call(gw, "entities_submit", {"entity_id": "E1"}, session)


@pytest.mark.positive
def test_f3_profile_switch_changes_the_clean_case_but_not_the_poisoned_one(tmp_path):
    gw = make_gateway(tmp_path, tools=tools())
    err, e = submit_after_screening(gw, "strict-clean", "clean")
    assert err and e["error"]["code"] == "APPROVAL_REQUIRED"          # strict: a human approves
    rewrite(gw, {"profile": "relaxed"})
    err, ok = submit_after_screening(gw, "relaxed-clean", "clean")
    assert not err and ok["result"]["status"] == "REVIEW"             # relaxed: clean case runs on its own
    err, e = submit_after_screening(gw, "relaxed-poisoned", "poisoned")
    assert err and e["error"]["code"] == "APPROVAL_REQUIRED"          # high_risk session: human, any profile
    assert gw.client.get("/admin/policy").json()["version"] == "v2"


@pytest.mark.negative
def test_removing_dlp_and_log_redaction_is_loud_and_restoring_them_works_without_restart(tmp_path):
    gw = make_gateway(tmp_path)
    secret = "sk-abcdefghijklmnop1234"
    assert chat(gw, f"use {secret}", "d1").status_code == 200
    assert secret not in gw.services.audit.path.read_text()
    rewrite(gw, remove_controls=["dlp.redact_inflight", "log.redact"])
    chat(gw, f"use {secret}", "d2")
    assert gw.client.get("/admin/posture").json()["score"] < 100
    assert any(e["event"] == "control.removed" for e in gw.services.audit.events(event="control.removed"))
    assert gw.services.audit.events(session="d2")[-1]["redaction"] == "off"
    rewrite(gw)  # restored
    chat(gw, f"use {secret}", "d3")
    assert gw.services.audit.events(session="d3")[-1]["redaction"] == "on"
    assert any(e["event"] == "control.restored" for e in gw.services.audit.events(event="control.restored"))


@pytest.mark.negative
def test_removing_the_baseline_control_is_rejected_and_the_old_policy_stays(tmp_path):
    gw = make_gateway(tmp_path)
    rewrite(gw, remove_controls=["auth.agent_key"])
    r = chat(gw, "hello", "base1")
    assert r.status_code == 200  # still served by the previous, valid policy
    p = gw.client.get("/admin/policy").json()
    assert p["version"] == "v1" and "baseline control" in p["error"]
    assert gw.services.audit.events(event="policy.rejected")
