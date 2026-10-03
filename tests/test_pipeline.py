from foureyes.core.control import Control, build_pipeline
from foureyes.core.pipeline import Pipeline
from foureyes.core.telemetry import Telemetry, percentile
from foureyes.core.types import Outcome, Verdict
from helpers import make_ctx, snapshot


class Fixed(Control):
    phases = ("pre", "post")

    def __init__(self, cid, verdict, cfg=None, layer="det"):
        super().__init__(cfg)
        self.id = cid
        self.verdict = verdict
        self.layer = layer
        self.calls = 0

    def evaluate(self, ctx, phase):
        self.calls += 1
        return self.verdict


class Boom(Control):
    id = "boom"

    def evaluate(self, ctx, phase):
        raise RuntimeError("kaput")


def run(controls, phase="pre"):
    ctx = make_ctx()
    return ctx, Pipeline(controls, Telemetry()).run(ctx, phase)


def test_most_severe_verdict_wins_and_block_short_circuits():
    a = Fixed("a", Verdict.redact("a"))
    b = Fixed("b", Verdict.approval("b"))
    c = Fixed("c", Verdict.block("c", code="X"))
    d = Fixed("d", Verdict.allow("d"))
    ctx, final = run([a, b, c, d])
    assert final.rule == "c" and final.outcome is Outcome.BLOCK
    assert d.calls == 0 and len(ctx.verdicts) == 3


def test_all_allow_returns_pipeline_allow():
    _, final = run([Fixed("a", None), Fixed("b", Verdict.allow("b"))])
    assert final.outcome is Outcome.ALLOW


def test_monitor_mode_logs_but_does_not_enforce():
    mon = Fixed("m", Verdict.block("m"), cfg={"mode": "monitor"})
    ctx, final = run([mon])
    assert final.outcome is Outcome.ALLOW
    assert ctx.monitor and ctx.monitor[0].rule == "m"


def test_control_exception_fails_closed():
    _, final = run([Boom()])
    assert final.outcome is Outcome.BLOCK and final.code == "CONTROL_ERROR"


def test_phase_filtering_and_spans():
    pre_only = Fixed("pre_only", Verdict.allow("x"))
    pre_only.phases = ("pre",)
    ctx, _ = run([pre_only], phase="post")
    assert pre_only.calls == 0
    ctx, _ = run([pre_only], phase="pre")
    assert ctx.spans and ctx.spans[0]["control"] == "pre_only"


def test_build_pipeline_orders_and_gates_by_catalog():
    class C(Control):
        phases = ("pre",)

        def evaluate(self, ctx, phase):
            return None

    def make(cid, hidden=False):
        return type("X" + cid.replace(".", "_"), (C,), {"id": cid, "hidden": hidden})

    reg = {cid: make(cid, hidden) for cid, hidden in
           [("auth.agent_key", False), ("route.invariant", True), ("authz.tools", False), ("sig.feed", False)]}
    snap = snapshot(remove_controls=["authz.tools"])
    pipe = build_pipeline(snap, Telemetry(), reg=reg)
    assert [c.id for c in pipe.controls] == ["auth.agent_key", "route.invariant", "sig.feed"]


def test_percentiles_and_snapshot():
    assert percentile([1, 2, 3, 4, 100], 50) == 3
    assert percentile([], 95) == 0.0
    t = Telemetry()
    for ms in (1.0, 2.0, 3.0):
        t.record_control("x", ms, "det")
    t.record_request(gateway_ms=4.0, upstream_ms=10.0)
    snap = t.snapshot()
    assert snap["controls"]["x"]["count"] == 3 and snap["controls"]["x"]["p50"] == 2.0
    assert snap["gateway"]["count"] == 1 and snap["upstream"]["p50"] == 10.0
    assert snap["layers"]["det"]["count"] == 3
