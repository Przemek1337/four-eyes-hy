from __future__ import annotations

import argparse
import os
import sys

import httpx

from . import (borderline_registry_extract, clean_registry_extract, developer_without_access,
               injected_registry_extract, uk_registry_extract)
from .demo_environment import DemoEnvironment, ScenarioResult

SCENARIOS = (clean_registry_extract, injected_registry_extract, borderline_registry_extract, uk_registry_extract,
             developer_without_access)


def run_all(env: DemoEnvironment) -> list[ScenarioResult]:
    return [scenario.run(env) for scenario in SCENARIOS]


def format_table(results: list[ScenarioResult]) -> str:
    lines = []
    for r in results:
        lines.append(f"{'PASS' if r.ok else 'FAIL'}  {r.name}")
        for what, expected, actual in r.checks:
            mark = "ok " if expected == actual else "XX "
            lines.append(f"      {mark}{what}: expected {expected!r}, actual {actual!r}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="make demo", description="Run every demo scenario against a running gateway.")
    p.add_argument("--gateway", default=os.environ.get("GATEWAY", "http://127.0.0.1:8080"))
    p.add_argument("--live-krs-number", default=os.environ.get("DEMO_LIVE_KRS_NUMBER", "0099000001"))
    args = p.parse_args(argv)
    env = DemoEnvironment(gateway=httpx.Client(base_url=args.gateway, timeout=300.0),
                          kyc_key=os.environ.get("KYC_AGENT_KEY", "dev-kyc_agent_key"),
                          dev_key=os.environ.get("ANETA_DEV_CLI_KEY", "dev-aneta_dev_cli_key"),
                          live_krs_number=args.live_krs_number)
    results = run_all(env)
    print(format_table(results))
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
