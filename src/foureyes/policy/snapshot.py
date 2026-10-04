from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from foureyes.core.types import Route
from foureyes.semantic.decision_model_types import BUILTIN_MODELS, decision_model_warnings

from .models import Policy
from .validator import validate
from .wall import wall_findings


class PolicySnapshot:
    """Immutable view of one validated policy version."""

    def __init__(self, snap_id: int, raw: dict, policy: Policy, base_dir: Path):
        self.id = snap_id
        self.raw = raw
        self.policy = policy
        self.base_dir = base_dir
        self._schemas: dict[str, dict | None] = {}
        self.wall: list[str] = wall_findings(policy)
        self.warnings: list[str] = decision_model_warnings(policy.decision_models, policy.controls) + [
            f"wall weakened: {f}" for f in self.wall]

    @classmethod
    def from_dict(cls, raw: dict, base_dir: Path = Path("."), snap_id: int = 1) -> "PolicySnapshot":
        return cls(snap_id, raw, validate(raw), Path(base_dir))

    @property
    def label(self) -> str:
        return f"v{self.id}"

    @property
    def controls(self) -> dict[str, dict]:
        return self.policy.controls

    @property
    def agents(self) -> dict[str, dict]:
        return self.policy.agents

    @property
    def tools(self) -> dict[str, dict]:
        return self.policy.tools

    @property
    def labels(self) -> dict:
        return self.policy.labels

    @property
    def budgets(self) -> dict:
        return self.policy.budgets

    @property
    def class_order(self) -> list[str]:
        return list(self.policy.data_classes["order"])

    def decision_models(self) -> dict[str, dict]:
        return {**BUILTIN_MODELS, **self.policy.decision_models}

    def decision_model_cfg(self, name: str) -> dict:
        return self.decision_models()[name]

    def has_control(self, cid: str) -> bool:
        return cid in self.policy.controls

    def control_cfg(self, cid: str) -> dict | None:
        return self.policy.controls.get(cid)

    def allowed_upstream_types(self, data_class: str) -> list[str]:
        return list(self.policy.data_classes["allowed_upstream_types"][data_class])

    def source_for(self, identity: str) -> dict:
        entry = self.policy.sources.get(identity)
        if isinstance(entry, dict):
            return {"class": entry["class"], "labels": list(entry.get("labels", [])),
                    "redact_fields": list(entry.get("redact_fields", []))}
        default = self.policy.sources.get("default_class", self.class_order[-1])
        return {"class": default, "labels": [], "redact_fields": []}

    def provider_type(self, provider: str) -> str:
        return self.policy.providers[provider]["type"]

    def provider_cost(self, provider: str) -> dict:
        return self.policy.providers.get(provider, {}).get("cost", {})

    def models(self) -> dict[str, dict]:
        return (self.policy.models or {}).get("allowlist", {})

    def model_provider(self, model: str) -> str | None:
        entry = self.models().get(model)
        return entry["provider"] if entry else None

    def first_model_of_type(self, ptype: str) -> str | None:
        for name, entry in self.models().items():
            if self.provider_type(entry["provider"]) == ptype:
                return name
        return None

    def default_local_model(self, agent_id: str | None) -> str | None:
        dm = self.agents.get(agent_id or "", {}).get("default_model")
        if dm and self.model_provider(dm) and self.provider_type(self.model_provider(dm)) == "local":
            return dm
        return self.first_model_of_type("local")

    def route_for(self, model: str, allowed: list[str], router: str = "default",
                  rerouted_from: str | None = None, fallback: bool = False) -> Route:
        provider = self.model_provider(model)
        return Route(provider=provider, type=self.provider_type(provider), model=model,
                     allowed_types=list(allowed), router=router,
                     rerouted_from=rerouted_from, fallback=fallback)

    def routing_value(self, key: str, default: Any = None) -> Any:
        return self.policy.routing.get(key, default)

    def dlp_value(self, kind: str, key: str, default: Any = None) -> Any:
        return (self.policy.dlp.get(kind) or {}).get(key, default)

    def team_of(self, agent_id: str) -> str | None:
        cfg = self.agents.get(agent_id, {})
        if cfg.get("team"):
            return cfg["team"]
        for team, tcfg in (self.budgets.get("teams") or {}).items():
            if agent_id in tcfg.get("agents", []):
                return team
        return None

    def tool_schema(self, tool: str) -> dict | None:
        if tool in self._schemas:
            return self._schemas[tool]
        schema = self.tools.get(tool, {}).get("schema")
        if isinstance(schema, str):
            schema = json.loads((self.base_dir / schema).read_text())
        self._schemas[tool] = schema
        return schema
