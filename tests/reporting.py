from __future__ import annotations

import json
import time
from pathlib import Path


CORPUS: list[dict] = []  # one row per synthetic attack or benign case, appended by the corpus tests


def record(kind: str, owasp: str, technique: str, stopped: bool, expected: str = "stop", sample: str = "") -> None:
    """kind "attack": `stopped` = the layer stopped it; expected "stop" (must) or "gap" (documented, measured only).
    kind "benign": `stopped` = the layer wrongly stopped a legitimate case (a false block)."""
    CORPUS.append({"kind": kind, "owasp": owasp, "technique": technique, "stopped": bool(stopped),
                   "expected": expected, "sample": sample[:80]})


def corpus_summary(rows: list[dict]) -> dict:
    attacks = [r for r in rows if r["kind"] == "attack"]
    benign = [r for r in rows if r["kind"] == "benign"]
    stopped = sum(r["stopped"] for r in attacks)
    by_owasp: dict[str, dict] = {}
    by_technique: dict[str, dict] = {}
    for r in rows:
        o = by_owasp.setdefault(r["owasp"], {"attacks": 0, "stopped": 0, "benign": 0, "false_blocks": 0})
        if r["kind"] == "attack":
            o["attacks"] += 1
            o["stopped"] += r["stopped"]
            t = by_technique.setdefault(r["technique"], {"attacks": 0, "stopped": 0})
            t["attacks"] += 1
            t["stopped"] += r["stopped"]
        else:
            o["benign"] += 1
            o["false_blocks"] += r["stopped"]
    gaps = [r for r in attacks if not r["stopped"]]
    return {"attacks": len(attacks), "attacks_stopped": stopped,
            "detection_rate": round(stopped / len(attacks), 4) if attacks else None,
            "benign": len(benign), "false_blocks": sum(r["stopped"] for r in benign),
            "false_block_rate": round(sum(r["stopped"] for r in benign) / len(benign), 4) if benign else None,
            "by_owasp": by_owasp, "by_technique": by_technique,
            "known_gaps": [{"owasp": r["owasp"], "technique": r["technique"], "sample": r["sample"]} for r in gaps[:40]],
            "known_gap_count": len(gaps)}


class ReportPlugin:
    def __init__(self):
        self.results: dict[str, bool] = {}

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or (report.when == "setup" and report.failed):
            self.results[report.nodeid] = report.passed

    def pytest_sessionfinish(self, session, exitstatus):
        data = {"passed": 0, "failed": 0, "positive": {"passed": 0, "failed": 0},
                "negative": {"passed": 0, "failed": 0}, "by_owasp": {}, "false_blocks": 0,
                "missed_attacks": 0, "ran_at": time.time(), "policy_version": "v1"}
        for item in session.items:
            if item.nodeid not in self.results:
                continue
            key = "passed" if self.results[item.nodeid] else "failed"
            data[key] += 1
            if item.get_closest_marker("positive"):
                data["positive"][key] += 1
                data["false_blocks"] += key == "failed"
            if item.get_closest_marker("negative"):
                data["negative"][key] += 1
                data["missed_attacks"] += key == "failed"
            for m in item.iter_markers("owasp"):
                data["by_owasp"].setdefault(m.args[0], {"passed": 0, "failed": 0})[key] += 1
        if CORPUS:
            data["corpus"] = corpus_summary(CORPUS)
        Path("reports").mkdir(exist_ok=True)
        Path("reports/test_report.json").write_text(json.dumps(data, indent=2))
