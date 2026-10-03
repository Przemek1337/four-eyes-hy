from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RouteMeta:
    """Everything a router may know. No message content, by design."""
    data_class: str
    task_type: str
    size_chars: int
    budget_remaining_pct: float | None
    available: tuple[str, ...]


@dataclass(frozen=True)
class RouteChoice:
    provider_type: str  # local | external
    router: str


class RoutingModel(Protocol):
    name: str

    def choose(self, meta: RouteMeta, allowed: list[str]) -> RouteChoice: ...


class RuleBasedRouter:
    """Deterministic stand-in for a decision model such as Jev (hosted API, not shipped)."""
    name = "rule_based"

    def __init__(self, external_min_chars: int = 1500, min_budget_pct: float = 10.0):
        self.external_min_chars = external_min_chars
        self.min_budget_pct = min_budget_pct

    def choose(self, meta: RouteMeta, allowed: list[str]) -> RouteChoice:
        if "external" in allowed and "external" in meta.available and meta.size_chars >= self.external_min_chars \
                and (meta.budget_remaining_pct is None or meta.budget_remaining_pct >= self.min_budget_pct):
            return RouteChoice("external", self.name)
        return RouteChoice("local", self.name)
