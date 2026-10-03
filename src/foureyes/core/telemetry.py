from __future__ import annotations

import threading
from collections import defaultdict, deque


def percentile(values, p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1))))
    return float(ordered[idx])


class Telemetry:
    def __init__(self, window: int = 2000):
        self._lock = threading.Lock()
        self._controls = defaultdict(lambda: deque(maxlen=window))
        self._layers = defaultdict(lambda: deque(maxlen=window))
        self._gateway = deque(maxlen=window)
        self._upstream = deque(maxlen=window)

    def record_control(self, control_id: str, ms: float, layer: str = "det") -> None:
        with self._lock:
            self._controls[control_id].append(ms)
            self._layers[layer].append(ms)

    def record_request(self, gateway_ms: float, upstream_ms: float) -> None:
        with self._lock:
            self._gateway.append(gateway_ms)
            self._upstream.append(upstream_ms)

    @staticmethod
    def _stats(values) -> dict:
        v = list(values)
        return {"count": len(v), "p50": percentile(v, 50), "p95": percentile(v, 95)}

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "controls": {k: self._stats(v) for k, v in self._controls.items()},
                "layers": {k: self._stats(v) for k, v in self._layers.items()},
                "gateway": self._stats(self._gateway),
                "upstream": self._stats(self._upstream),
            }
