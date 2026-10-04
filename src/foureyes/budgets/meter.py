from __future__ import annotations

import sqlite3
import threading
import time
from typing import Callable


class MeterStore:
    """Usage counters in SQLite, so a restart does not reset budgets."""

    def __init__(self, path: str = ":memory:", clock: Callable[[], float] = time.time):
        self.clock = clock
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute("CREATE TABLE IF NOT EXISTS usage (scope TEXT, scope_id TEXT, metric TEXT, "
                             "win TEXT, value REAL, PRIMARY KEY (scope, scope_id, metric, win))")
            self._db.execute("CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER)")
            self._db.commit()

    def _day(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime(self.clock()))

    def _month(self) -> str:
        return time.strftime("%Y-%m", time.gmtime(self.clock()))

    def _inc(self, scope: str, scope_id: str, metric: str, win: str, amount: float) -> None:
        self._db.execute(
            "INSERT INTO usage VALUES (?,?,?,?,?) ON CONFLICT(scope, scope_id, metric, win) "
            "DO UPDATE SET value = value + excluded.value", (scope, scope_id, metric, win, amount))

    def add(self, agent: str, team: str | None, provider_type: str, tokens: int,
            usd: float = 0.0, compute_s: float = 0.0) -> None:
        with self._lock:
            day = self._day()
            self._inc("agent", agent, "tokens", day, tokens)
            if provider_type == "external":
                self._inc("agent", agent, "usd", day, usd)
                if team:
                    self._inc("team", team, "usd", self._month(), usd)
            else:
                self._inc("agent", agent, "usd_local", day, usd)
                self._inc("agent", agent, "compute_s", day, compute_s)
            self._db.commit()

    def _get(self, scope: str, scope_id: str, metric: str, win: str) -> float:
        with self._lock:
            row = self._db.execute("SELECT value FROM usage WHERE scope=? AND scope_id=? AND metric=? AND win=?",
                                   (scope, scope_id, metric, win)).fetchone()
        return float(row[0]) if row else 0.0

    def agent_daily(self, agent: str, metric: str) -> float:
        return self._get("agent", agent, metric, self._day())

    def team_monthly(self, team: str, metric: str = "usd") -> float:
        return self._get("team", team, metric, self._month())

    def count(self, name: str, n: int = 1) -> None:
        with self._lock:
            self._db.execute("INSERT INTO counters VALUES (?,?) ON CONFLICT(name) DO UPDATE SET value = value + ?",
                             (name, n, n))
            self._db.commit()

    def get_count(self, name: str) -> int:
        with self._lock:
            row = self._db.execute("SELECT value FROM counters WHERE name=?", (name,)).fetchone()
        return int(row[0]) if row else 0

    def external_remaining_pct(self, agent_id: str | None, snapshot) -> float | None:
        limit = (snapshot.budgets.get("agents") or {}).get(agent_id or "", {}).get("daily_usd")
        if not limit:
            return None
        return max(0.0, (1 - self.agent_daily(agent_id, "usd") / limit) * 100)

    def usage_summary(self, snapshot) -> dict:
        soft = snapshot.budgets.get("soft_limit_pct", 80)

        def level(pct: float | None) -> str:
            if pct is None:
                return "ok"
            return "over" if pct >= 100 else "warn" if pct >= soft else "ok"

        agents = []
        for agent, lim in (snapshot.budgets.get("agents") or {}).items():
            used_usd = self.agent_daily(agent, "usd")
            used_cs = self.agent_daily(agent, "compute_s")
            pcts = []
            if lim.get("daily_usd"):
                pcts.append(used_usd / lim["daily_usd"] * 100)
            if lim.get("daily_compute_seconds"):
                pcts.append(used_cs / lim["daily_compute_seconds"] * 100)
            pct = max(pcts) if pcts else None
            agents.append({"agent": agent, "team": snapshot.team_of(agent), "usd_used": used_usd,
                           "usd_limit": lim.get("daily_usd"), "compute_used": used_cs,
                           "compute_limit": lim.get("daily_compute_seconds"),
                           "pct": pct, "level": level(pct)})
        teams = []
        for team, lim in (snapshot.budgets.get("teams") or {}).items():
            used = self.team_monthly(team)
            pct = used / lim["monthly_usd"] * 100 if lim.get("monthly_usd") else None
            teams.append({"team": team, "usd_used": used, "usd_limit": lim.get("monthly_usd"),
                          "pct": pct, "level": level(pct)})
        return {"agents": agents, "teams": teams,
                "blocked_by_budget": self.get_count("budget_blocked"),
                "fallbacks": self.get_count("budget_fallback")}
