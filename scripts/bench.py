"""Gateway overhead benchmark with mock upstreams (no GPU, no network)."""
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path[:0] = ["src", "tests"]
from helpers import chat, make_gateway  # noqa: E402


def run(n: int = 200) -> dict:
    gw = make_gateway(Path(tempfile.mkdtemp()))
    for i in range(n):
        chat(gw, "Verify client Nordwind Sp. z o.o.", f"bench{i % 20}")
    t = gw.services.telemetry.snapshot()
    return {"requests": n, "gateway_p50_ms": t["gateway"]["p50"], "gateway_p95_ms": t["gateway"]["p95"],
            "per_control_p95_ms": {k: v["p95"] for k, v in sorted(t["controls"].items(), key=lambda kv: -kv[1]["p95"])[:5]}}


if __name__ == "__main__":
    print(run())
