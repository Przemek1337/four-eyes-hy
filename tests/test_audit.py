import csv
import io
import json

from foureyes.audit.sink import AuditSink
from helpers import snapshot

PESEL = "44051401359"


def sink(tmp_path, **kw):
    snap = snapshot(**kw)
    return AuditSink(tmp_path / "audit.jsonl", lambda: snap)


def decision(**over):
    ev = {"event": "decision", "session_id": "s1", "agent": "kyc-agent", "decision": "ALLOW",
          "rule": "pipeline", "owasp": ["LLM02:2026"], "content": f"my pesel is {PESEL}"}
    ev.update(over)
    return ev


def test_log_redaction_on_writes_no_pii_to_file_and_memory(tmp_path):
    s = sink(tmp_path)
    s.emit(decision())
    line = (tmp_path / "audit.jsonl").read_text()
    assert PESEL not in line and "[REDACTED]" in line
    assert json.loads(line)["redaction"] == "on"
    assert PESEL not in json.dumps(s.events())


def test_removing_log_redact_is_loud_and_leaves_raw_data(tmp_path):
    s = sink(tmp_path, remove_controls=["log.redact"])
    out = s.emit(decision())
    assert PESEL in out["content"] and out["redaction"] == "off"


def test_monitor_mode_does_not_redact_but_is_flagged(tmp_path):
    s = sink(tmp_path, overrides={"controls": {"log.redact": {"mode": "monitor"}}})
    out = s.emit(decision())
    assert PESEL in out["content"] and out["redaction"] == "monitor"


def test_filters_and_exports(tmp_path):
    s = sink(tmp_path)
    s.emit(decision(decision="BLOCK", rule="authz.tools", agent="a1", owasp=["LLM03:2026"]))
    s.emit(decision(decision="ALLOW", agent="a2"))
    blocks = s.events(decision="BLOCK")
    assert len(blocks) == 1 and blocks[0]["rule"] == "authz.tools"
    assert len(s.events(owasp="LLM03:2026")) == 1
    assert len(s.events(agent="a2")) == 1

    jsonl = s.export("jsonl", decision="BLOCK")
    assert len(jsonl.strip().splitlines()) == 1

    rows = list(csv.DictReader(io.StringIO(s.export("csv"))))
    assert len(rows) == 2
    assert list(rows[0].keys()) == AuditSink.COLUMNS
    assert rows[0]["owasp"] == "LLM03:2026"
    assert PESEL not in s.export("csv") and PESEL not in s.export("jsonl")


def test_subscribers_receive_events(tmp_path):
    s = sink(tmp_path)
    q = s.subscribe()
    s.emit(decision())
    assert q.get(timeout=1)["session_id"] == "s1"
    s.unsubscribe(q)
