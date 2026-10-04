import threading
from types import SimpleNamespace

import pytest

from foureyes.budgets.meter import MeterStore
from foureyes.controls.budget import BudgetSession, BudgetSpend
from foureyes.core.types import Outcome
from helpers import make_ctx, snapshot

POLICY_ROUTE = {"local": "basal-1.0-1.5B", "external": "ext-gpt-sim"}


def model_ctx(route="external", meter=None, overrides=None, text="hi", session=None):
    meter = meter or MeterStore()
    ctx = make_ctx(overrides=overrides, services=SimpleNamespace(meter=meter), session=session,
                   messages=[{"role": "user", "content": text}], params={"max_tokens": 256})
    ctx.route = ctx.policy.route_for(POLICY_ROUTE[route], ["local", "external"])
    return ctx, meter


def test_meter_accumulates_per_agent_and_team():
    m = MeterStore()
    m.add("kyc-agent", "compliance", "external", tokens=150, usd=0.0025)
    m.add("kyc-agent", "compliance", "local", tokens=150, usd=0.0001, compute_s=0.2)
    assert m.agent_daily("kyc-agent", "usd") == pytest.approx(0.0025)
    assert m.agent_daily("kyc-agent", "compute_s") == pytest.approx(0.2)
    assert m.agent_daily("kyc-agent", "tokens") == 300
    assert m.team_monthly("compliance") == pytest.approx(0.0025)


def test_meter_is_thread_safe():
    m = MeterStore()
    ts = [threading.Thread(target=lambda: [m.add("a", "t", "external", 1, usd=1.0) for _ in range(10)]) for _ in range(20)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert m.agent_daily("a", "usd") == 200.0


def test_session_limits_with_agent_override():
    ctx, _ = model_ctx()
    ctx.session.steps = 20
    assert BudgetSession().evaluate(ctx, "pre") is None
    ctx.session.steps = 21
    v = BudgetSession().evaluate(ctx, "pre")
    assert v.code == "SESSION_STEPS_EXCEEDED" and v.owasp == ("LLM06:2026", "ASI08")
    tight, _ = model_ctx(overrides={"agents": {"kyc-agent": {"overrides": {"budget.session": {"max_steps": 5}}}}})
    tight.session.steps = 6
    assert BudgetSession().evaluate(tight, "pre").code == "SESSION_STEPS_EXCEEDED"
    toks, _ = model_ctx()
    toks.session.tokens = 20000
    assert BudgetSession().evaluate(toks, "pre").code == "SESSION_TOKENS_EXCEEDED"


@pytest.mark.positive
def test_within_budget_is_allowed_and_cost_is_settled():
    ctx, meter = model_ctx()
    assert BudgetSpend().evaluate(ctx, "pre") is None
    ctx.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    BudgetSpend().evaluate(ctx, "post")
    assert ctx.notes["cost_usd"] == pytest.approx(0.0025)
    assert meter.agent_daily("kyc-agent", "usd") == pytest.approx(0.0025)
    assert ctx.session.tokens == 150


@pytest.mark.negative
@pytest.mark.owasp("LLM06:2026")
def test_exceeding_daily_usd_blocks_before_the_model_is_called():
    ctx, meter = model_ctx()
    meter.add("kyc-agent", "compliance", "external", 0, usd=1.999)
    v = BudgetSpend().evaluate(ctx, "pre")
    assert v.outcome is Outcome.BLOCK and v.code == "BUDGET_EXCEEDED"
    assert meter.get_count("budget_blocked") == 1


@pytest.mark.negative
def test_exceeding_local_compute_seconds_blocks():
    ctx, meter = model_ctx(route="local")
    meter.add("kyc-agent", "compliance", "local", 0, usd=0.0, compute_s=600)
    assert BudgetSpend().evaluate(ctx, "pre").code == "BUDGET_EXCEEDED"


@pytest.mark.negative
def test_team_monthly_limit_applies_across_agents():
    ctx, meter = model_ctx()
    meter.add("playground-agent", "compliance", "external", 0, usd=49.999)
    assert BudgetSpend().evaluate(ctx, "pre").code == "BUDGET_EXCEEDED"


def test_soft_limit_alerts_but_allows():
    ctx, meter = model_ctx()
    meter.add("kyc-agent", "compliance", "external", 0, usd=1.7)
    assert BudgetSpend().evaluate(ctx, "pre") is None
    assert any(a["kind"] == "budget.soft" for a in ctx.alerts)


def test_fallback_local_reroutes_instead_of_blocking():
    ctx, meter = model_ctx(overrides={"budgets": {"on_exceeded": "fallback_local"}})
    meter.add("kyc-agent", "compliance", "external", 0, usd=1.999)
    v = BudgetSpend().evaluate(ctx, "pre")
    assert v.outcome is Outcome.ALLOW and ctx.route.type == "local" and ctx.route.fallback is True
    assert meter.get_count("budget_fallback") == 1


def test_fallback_local_still_blocks_when_local_is_also_exhausted():
    ctx, meter = model_ctx(overrides={"budgets": {"on_exceeded": "fallback_local"}})
    meter.add("kyc-agent", "compliance", "external", 0, usd=1.999)
    meter.add("kyc-agent", "compliance", "local", 0, compute_s=600)
    assert BudgetSpend().evaluate(ctx, "pre").outcome is Outcome.BLOCK


def test_on_exceeded_approval_and_live_limit_change():
    ctx, meter = model_ctx(overrides={"budgets": {"on_exceeded": "approval"}})
    meter.add("kyc-agent", "compliance", "external", 0, usd=1.999)
    assert BudgetSpend().evaluate(ctx, "pre").outcome is Outcome.APPROVAL

    low, meter2 = model_ctx(overrides={"budgets": {"agents": {"kyc-agent": {"daily_usd": 0.5}}}})
    meter2.add("kyc-agent", "compliance", "external", 0, usd=0.6)
    assert BudgetSpend().evaluate(low, "pre").code == "BUDGET_EXCEEDED"


def test_external_remaining_pct_and_summary():
    m = MeterStore()
    snap = snapshot()
    assert m.external_remaining_pct("kyc-agent", snap) == 100.0
    m.add("kyc-agent", "compliance", "external", 0, usd=0.5)
    assert m.external_remaining_pct("kyc-agent", snap) == pytest.approx(75.0)
    assert m.external_remaining_pct("unknown", snap) is None
    row = next(r for r in m.usage_summary(snap)["agents"] if r["agent"] == "kyc-agent")
    assert row["usd_used"] == pytest.approx(0.5) and row["level"] == "ok" and row["pct"] == pytest.approx(25.0)
