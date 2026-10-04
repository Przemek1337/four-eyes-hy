"""Send the staged attack demo to a RUNNING gateway, all at once, so the dashboard has something to show.

    make run            # in one terminal (MODEL=mock make run works offline)
    make demo-traffic   # in another; then open http://127.0.0.1:8080/ui/

The same scenarios run from the Playground's "Run test attack" button, one at a time. About 80 requests, a few seconds
here. Everything uses fictitious data. At the end it checks every request against what the policy should do and exits
non-zero if an attack got through or a legitimate request was stopped. Cases that depend on the model's wording are shown
but not counted."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from harness.kyc.attack_demo import Gateway, Run, run_all  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--base", default=os.environ.get("GATEWAY", "http://127.0.0.1:8080"))
    p.add_argument("--key", default=os.environ.get("KYC_AGENT_KEY", "dev-kyc_agent_key"))
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--pace", type=float, default=0.0, help="seconds to wait between requests")
    args = p.parse_args()
    http = httpx.Client(base_url=args.base, timeout=60.0)
    try:
        http.get("/metrics").raise_for_status()
    except httpx.HTTPError as exc:
        print(f"No gateway at {args.base} ({exc}). Start it first: make run", file=sys.stderr)
        return 2

    def show(row: dict) -> None:
        mark = "  ·" if row["ok"] is None else (" ok" if row["ok"] else "!!!")
        note = f"  [{row['note']}]" if row["note"] else ""
        print(f"{mark} {row['owasp']:11} {row['actual']:9} {row['label'][:70]}{note}")

    run = Run(pace=args.pace, on_row=show, seed=args.seed)
    print(f"Sending demo traffic to {args.base} (sessions {run.prefix}-*)\n")
    s = run_all(Gateway(http, args.key), run)
    print(f"\n{s['sent']} requests. Attacks stopped: {s['attacks_stopped']}/{s['attacks']}. "
          f"Legitimate requests passed: {s['legit_passed']}/{s['legit']}. Not counted (model-dependent): {s['uncounted']}.")
    for note in s["notes"]:
        print(f"  note: {note}")
    if s["unexpected"]:
        print("\nUNEXPECTED:")
        for line in s["unexpected"]:
            print(f"  {line}")
    pending = http.get("/admin/approvals").json().get("approvals", [])
    print(f"\nOpen the dashboard: {args.base}/ui/   ({len(pending)} approval(s) waiting for a human on the Security tab)")
    return 1 if s["unexpected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
