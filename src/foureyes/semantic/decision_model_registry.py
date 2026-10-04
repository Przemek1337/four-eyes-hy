from __future__ import annotations

import json
import threading
from typing import Callable

from .basal_decision_client import BasalDecisionClient
from .decision_model_client import DecisionModelClient
from .decision_model_types import LEGACY_MODELS, model_refs
from .granite_guardian_decision_client import GraniteGuardianDecisionClient
from .mock_decision_client import MockDecisionClient

Factory = Callable[[dict], DecisionModelClient]

DEFAULT_FACTORIES: dict[str, Factory] = {
    "basal": BasalDecisionClient.from_config,
    "granite_guardian": GraniteGuardianDecisionClient.from_config,
    "mock": lambda cfg: MockDecisionClient(),
}


class DecisionModelRegistry:
    """Hands out decision model clients by the names used in policy.yaml. A changed config builds a new client,
    so a hot reload that points a model elsewhere takes effect on the next request."""

    def __init__(self, factories: dict[str, Factory] | None = None, override: DecisionModelClient | None = None):
        self.factories = {**DEFAULT_FACTORIES, **(factories or {})}
        self.override = override
        self._cache: dict[tuple[str, str], DecisionModelClient] = {}
        self._lock = threading.Lock()

    def client(self, name: str, snapshot) -> DecisionModelClient:
        if self.override is not None:
            return self.override
        cfg = snapshot.decision_model_cfg(name)
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
            try:
                out[name] = bool(self.client(name, snapshot).healthy())
            except Exception:
                out[name] = False
        return out
