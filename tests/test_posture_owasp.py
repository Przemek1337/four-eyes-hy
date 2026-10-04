import pytest

from foureyes.owasp import CATEGORIES, coverage
from foureyes.posture import compute
from helpers import snapshot

OK_FEED = {"version": "v", "count": 7, "last_reload": 1.0, "error": None}


def test_full_policy_scores_100_with_no_breakdown():
    p = compute(snapshot(), ai_healthy=True, feed_status=OK_FEED, tests=None)
    assert p["score"] == 100 and p["breakdown"] == []


def test_removed_control_drops_score_with_explicit_line_item():
    p = compute(snapshot(remove_controls=["dlp.redact_inflight"]), ai_healthy=True, feed_status=OK_FEED, tests=None)
    assert p["score"] < 100
    item = next(b for b in p["breakdown"] if b["item"] == "dlp.redact_inflight")
    assert item["delta"] < 0 and item["note"] == "removed"


def test_monitor_mode_costs_half_of_removal():
    removed = compute(snapshot(remove_controls=["output.safe"]), ai_healthy=True, feed_status=OK_FEED, tests=None)
    monitor = compute(snapshot(overrides={"controls": {"output.safe": {"mode": "monitor"}}}), ai_healthy=True,
                      feed_status=OK_FEED, tests=None)
    r = next(b for b in removed["breakdown"] if b["item"] == "output.safe")["delta"]
    m = next(b for b in monitor["breakdown"] if b["item"] == "output.safe")["delta"]
    assert m == pytest.approx(r / 2, abs=0.11)


def test_penalties_for_feed_ai_model_and_failing_tests():
    snap = snapshot()
    assert compute(snap, ai_healthy=False, feed_status=OK_FEED, tests=None)["score"] == 90
    assert compute(snap, ai_healthy=True, feed_status={**OK_FEED, "error": "boom"}, tests=None)["score"] == 90
    assert compute(snap, ai_healthy=True, feed_status=OK_FEED, tests={"failed": 2})["score"] == 90
    worst = compute(snapshot(remove_controls=list(snapshot().controls) [1:]), ai_healthy=False,
                    feed_status={**OK_FEED, "error": "x"}, tests={"failed": 1})
    assert 0 <= worst["score"] < 100


def by_id(cov):
    return {c["id"]: c for c in cov["categories"]}


def test_all_controls_active_covers_nine_of_ten_and_is_honest_about_llm07():
    cov = by_id(coverage(snapshot(), blocks={}, tested_ids=set()))
    assert len(CATEGORIES) == 10
    enforced = [c for c in cov.values() if c["status"] == "enforced"]
    assert len(enforced) == 9 and cov["LLM07:2026"]["status"] == "uncovered"
    assert "out of scope" in cov["LLM07:2026"]["note"]


def test_removing_every_llm02_control_makes_it_uncovered_and_monitor_makes_it_yellow():
    llm02 = ["data.classify_net", "route.model", "dlp.redact_inflight", "log.redact"]
    gone = by_id(coverage(snapshot(remove_controls=llm02), blocks={}, tested_ids=set()))
    assert gone["LLM02:2026"]["status"] == "uncovered"
    mon = by_id(coverage(snapshot(overrides={"controls": {c: {"mode": "monitor"} for c in llm02}}), blocks={}, tested_ids=set()))
    assert mon["LLM02:2026"]["status"] == "monitor_only"
    partial = by_id(coverage(snapshot(remove_controls=llm02[:3]), blocks={}, tested_ids=set()))
    assert partial["LLM02:2026"]["status"] == "enforced"


def test_blocks_and_tested_counters():
    out = coverage(snapshot(), blocks={"LLM01:2026": 5}, tested_ids={"LLM01:2026", "LLM02:2026"})
    assert by_id(out)["LLM01:2026"]["blocks"] == 5 and out["tested"] == "2/10" and out["edition"] == "2026"
