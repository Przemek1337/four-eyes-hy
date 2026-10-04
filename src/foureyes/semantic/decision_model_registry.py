from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Callable

from .basal_decision_client import BasalDecisionClient
from .decision_model_client import DecisionModelClient
from .decision_model_types import LEGACY_MODELS, model_refs
from .granite_guardian_decision_client import GraniteGuardianDecisionClient
from .mock_decision_client import MockDecisionClient

Factory = Callable[[dict], DecisionModelClient]

_ENV_REF = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")


def expand_env(value: str) -> str:
    """`${VAR}` / `${VAR:-default}` in a model URL, so one policy works on the host and inside containers."""
    return _ENV_REF.sub(lambda m: os.environ.get(m.group(1)) or (m.group(2) or ""), value)

DEFAULT_FACTORIES: dict[str, Factory] = {
    "basal": BasalDecisionClient.from_config,
    "granite_guardian": GraniteGuardianDecisionClient.from_config,
    "mock": lambda cfg: MockDecisionClient(),
}


class DecisionModelRegistry:
    """Hands out decision model clients by the names used in policy.yaml. A changed config builds a new client,
    so a hot reload that points a model elsewhere takes effect on the next request."""

    def __init__(self, factories: dict[str, Factory] | None = None, override: DecisionModelClient | None = None,
                 health_ttl_s: float = 5.0, clock: Callable[[], float] = time.monotonic):
        self.factories = {**DEFAULT_FACTORIES, **(factories or {})}
        self.override = override
        self._cache: dict[tuple[str, str], DecisionModelClient] = {}
        self._lock = threading.Lock()
        self.health_ttl_s = health_ttl_s
        self._clock = clock
        self._health: dict[tuple[str, str], tuple[float, bool]] = {}

    def client(self, name: str, snapshot) -> DecisionModelClient:
        if self.override is not None:
            return self.override
        cfg = snapshot.decision_model_cfg(name)
        if isinstance(cfg.get("base_url"), str):
            cfg = {**cfg, "base_url": expand_env(cfg["base_url"])}
        key = (name, json.dumps(cfg, sort_keys=True))
        with self._lock:
            if key not in self._cache:
                factory = self.factories.get(cfg["type"])
                if factory is None:
                    raise KeyError(f"no adapter for decision model type {cfg['type']!r}")
                self._cache[key] = factory(cfg)
            return self._cache[key]

    def health(self, snapshot) -> dict[str, bool]:
        names = {name for cid, name in model_refs(snapshot.controls).items()
                 if name not in LEGACY_MODELS.get(cid, ())}
        out: dict[str, bool] = {}
        for name in sorted(names):
            key = (name, json.dumps(snapshot.decision_model_cfg(name), sort_keys=True))
            now = self._clock()
            with self._lock:
                hit = self._health.get(key)
            if hit is not None and now - hit[0] < self.health_ttl_s:
                out[name] = hit[1]
                continue
            try:
                ok = bool(self.client(name, snapshot).healthy())
            except Exception:
                ok = False
            with self._lock:
                self._health[key] = (now, ok)
            out[name] = ok
        return out
