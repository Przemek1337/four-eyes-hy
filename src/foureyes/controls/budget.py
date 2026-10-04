from foureyes.core.control import Control, register
from foureyes.core.types import Verdict

OWASP = ("LLM06:2026", "ASI08")


@register
class BudgetSession(Control):
    id = "budget.session"
    phases = ("pre",)

    def evaluate(self, ctx, phase):
        cfg = {**ctx.policy.budgets.get("session", {}), **ctx.overrides(self.id)}
        if cfg.get("max_steps") and ctx.session.steps > cfg["max_steps"]:
            return Verdict.block(self.id, f"session exceeded {cfg['max_steps']} steps", code="SESSION_STEPS_EXCEEDED", owasp=OWASP)
        if cfg.get("max_tokens") and ctx.session.tokens >= cfg["max_tokens"]:
            return Verdict.block(self.id, f"session exceeded {cfg['max_tokens']} tokens", code="SESSION_TOKENS_EXCEEDED", owasp=OWASP)
        return None


@register
class BudgetSpend(Control):
    id = "budget.spend"
    phases = ("pre", "post")

    # ---- helpers -------------------------------------------------------------------------
    def _exceeded(self, ctx, route) -> tuple[bool, float | None]:
        """Return (exceeded, highest usage percentage) for the route's provider type."""
        meter, req, pol = ctx.services.meter, ctx.request, ctx.policy
        limits = (pol.budgets.get("agents") or {}).get(req.agent_id or "", {})
        if route.type == "external":
            cost = self._estimate_usd(ctx, route)
            pcts, over = [], False
            if limits.get("daily_usd"):
                used = meter.agent_daily(req.agent_id, "usd")
                over |= used + cost > limits["daily_usd"]
                pcts.append(used / limits["daily_usd"] * 100)
            team = pol.team_of(req.agent_id or "")
            tl = (pol.budgets.get("teams") or {}).get(team or "", {})
            if tl.get("monthly_usd"):
                used = meter.team_monthly(team)
                over |= used + cost > tl["monthly_usd"]
                pcts.append(used / tl["monthly_usd"] * 100)
            return over, max(pcts) if pcts else None
        if limits.get("daily_compute_seconds"):
            used = meter.agent_daily(req.agent_id, "compute_s")
            return used >= limits["daily_compute_seconds"], used / limits["daily_compute_seconds"] * 100
        return False, None

    @staticmethod
    def _estimate_usd(ctx, route) -> float:
        rates = ctx.policy.provider_cost(route.provider)
        tokens_in = max(1, len(ctx.request.full_text) // 4)
        tokens_out = ctx.request.params.get("max_tokens", 256)
        return tokens_in / 1000 * rates.get("input_per_1k", 0) + tokens_out / 1000 * rates.get("output_per_1k", 0)

    # ---- evaluate ------------------------------------------------------------------------
    def evaluate(self, ctx, phase):
        if ctx.request.kind != "model" or ctx.route is None:
            return None
        return self._pre(ctx) if phase == "pre" else self._settle(ctx)

    def _pre(self, ctx):
        route = ctx.route
        exceeded, pct = self._exceeded(ctx, route)
        soft = ctx.policy.budgets.get("soft_limit_pct", 80)
        if pct is not None and pct >= soft and not exceeded:
            ctx.alert("budget.soft", pct=round(pct, 1), provider=route.type)
        if not exceeded:
            return None
        meter = ctx.services.meter
        action = ctx.policy.budgets.get("on_exceeded", "block")
        if action == "fallback_local" and route.type == "external":
            local = ctx.policy.default_local_model(ctx.request.agent_id)
            if local:
                fallback = ctx.policy.route_for(local, route.allowed_types, router="budget_fallback", fallback=True)
                if not self._exceeded(ctx, fallback)[0]:
                    ctx.route = fallback
                    meter.count("budget_fallback")
                    return Verdict.allow(self.id, "external budget exhausted; routed to local model", owasp=OWASP,
                                         detail={"fallback_local": True})
        meter.count("budget_blocked")
        if action == "approval":
            return Verdict.approval(self.id, "budget exceeded; compliance approval required", code="BUDGET_APPROVAL", owasp=OWASP)
        return Verdict.block(self.id, "budget exceeded", code="BUDGET_EXCEEDED", owasp=OWASP)

    def _settle(self, ctx):
        usage, route, req = ctx.usage, ctx.route, ctx.request
        if not usage:
            return None
        ctx.session.add_tokens(int(usage.get("total_tokens", 0)))
        rates = ctx.policy.provider_cost(route.provider)
        team = ctx.policy.team_of(req.agent_id or "")
        if route.type == "external":
            usd = (usage.get("prompt_tokens", 0) / 1000 * rates.get("input_per_1k", 0)
                   + usage.get("completion_tokens", 0) / 1000 * rates.get("output_per_1k", 0))
            ctx.services.meter.add(req.agent_id, team, "external", usage.get("total_tokens", 0), usd=usd)
            ctx.notes["cost_usd"], ctx.notes["compute_s"] = usd, 0.0
        else:
            secs = ctx.upstream_seconds
            usd = secs * rates.get("per_compute_second", 0)
            ctx.services.meter.add(req.agent_id, team, "local", usage.get("total_tokens", 0), usd=usd, compute_s=secs)
            ctx.notes["cost_usd"], ctx.notes["compute_s"] = usd, secs
        return None
