import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bench  # noqa: E402


def test_gateway_overhead_stays_small_with_mock_upstreams():
    out = bench.run(60)
    assert out["gateway_p95_ms"] < 50, out  # deterministic controls + mock AI; generous bound for CI laptops
