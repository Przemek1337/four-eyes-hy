from __future__ import annotations

import json
import time
from pathlib import Path


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
        Path("reports").mkdir(exist_ok=True)
        Path("reports/test_report.json").write_text(json.dumps(data, indent=2))
