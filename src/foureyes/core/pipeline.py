from __future__ import annotations

import time

from .control import Control
from .context import Ctx
from .types import Outcome, Verdict


class Pipeline:
    def __init__(self, controls: list[Control], telemetry):
        self.controls = controls
        self.telemetry = telemetry

    def run(self, ctx: Ctx, phase: str) -> Verdict:
        final = Verdict.allow("pipeline")
        for ctl in self.controls:
            if phase not in ctl.phases:
                continue
            v = self._run_one(ctl, ctx, phase)
            if v is None:
                continue
            if ctl.monitoring and v.outcome is not Outcome.ALLOW:
                ctx.monitor.append(v)
                continue
            ctx.verdicts.append(v)
            if v.stricter_than(final):
                final = v
            if v.outcome is Outcome.BLOCK:
                break
        return final

    def _run_one(self, ctl: Control, ctx: Ctx, phase: str) -> Verdict | None:
        t0 = time.perf_counter()
        try:
            v = ctl.evaluate(ctx, phase)
        except Exception as exc:  # fail-closed
            v = Verdict.block(ctl.id, f"control error: {exc}", code="CONTROL_ERROR")
        ms = (time.perf_counter() - t0) * 1000
        if self.telemetry is not None:
            self.telemetry.record_control(ctl.id, ms, ctl.layer)
        ctx.spans.append({"control": ctl.id, "phase": phase, "ms": round(ms, 3),
                          "outcome": v.outcome.value if v else "SKIP"})
        return v
