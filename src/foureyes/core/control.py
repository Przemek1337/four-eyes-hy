from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from .context import Ctx
from .types import Verdict

# Fixed evaluation order. Only controls present in policy `controls:` run (plus hidden baseline stages).
ORDER = (
    "auth.agent_key", "source.stage", "models.allowlist", "authz.tools", "authz.tool_schema",
    "authz.scope", "data.classify_net", "route.invariant", "route.model", "budget.session",
    "budget.spend", "sig.feed", "sem.prompt_injection", "flow.untrusted", "sem.action_judge",
    "dlp.redact_inflight", "output.safe",
)


class Control(ABC):
    id: ClassVar[str]
    phases: ClassVar[tuple[str, ...]] = ("pre",)
    hidden: ClassVar[bool] = False  # hidden = always on, defined in code, not in the catalog
    layer: ClassVar[str] = "det"  # det | ai

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or {}
        self.mode = self.cfg.get("mode", "enforce")

    @property
    def monitoring(self) -> bool:
        return self.mode == "monitor"

    def conf(self, ctx: Ctx) -> dict:
        """Control config with per-agent overrides merged on top (shallow)."""
        return {**self.cfg, **ctx.overrides(self.id)}

    @abstractmethod
    def evaluate(self, ctx: Ctx, phase: str) -> Verdict | None: ...


_REGISTRY: dict[str, type[Control]] = {}


def register(cls: type[Control]) -> type[Control]:
    _REGISTRY[cls.id] = cls
    return cls


def registry() -> dict[str, type[Control]]:
    return _REGISTRY


def build_pipeline(snapshot, telemetry, reg: dict[str, type[Control]] | None = None):
    from .pipeline import Pipeline

    reg = _REGISTRY if reg is None else reg
    controls: list[Control] = []
    for cid in ORDER:
        cls = reg.get(cid)
        if cls is None:
            continue
        if cls.hidden or snapshot.has_control(cid):
            controls.append(cls(snapshot.control_cfg(cid) or {}))
    return Pipeline(controls, telemetry)
