from __future__ import annotations

from foureyes.core.control import Control, register
from foureyes.core.types import Verdict
from foureyes.routing.router import RouteChoice, RouteMeta

OWASP = ("LLM02:2026",)


@register
class RouteInvariant(Control):
    """Baseline, in code: the allowed upstream types are a function of the session data class."""
    id = "route.invariant"
    phases = ("pre",)
    hidden = True

    def evaluate(self, ctx, phase):
        if ctx.request.kind != "model":
            return None
        pol = ctx.policy
        agent = ctx.request.agent_id
        allowed = pol.allowed_upstream_types(ctx.session.data_class)
        model = ctx.request.model or "auto"

        if model == "auto":
            local = pol.default_local_model(agent)
            if local is None:
                return Verdict.block(self.id, "no local model configured", code="LOCAL_UNAVAILABLE", owasp=OWASP)
            ctx.route = pol.route_for(local, allowed, router="default")
            return None

        if pol.model_provider(model) is None:
            return Verdict.block(self.id, f"model {model!r} is not in the allowlist",
                                 code="MODEL_NOT_ALLOWED", owasp=("LLM03:2026",))
        route = pol.route_for(model, allowed, router="explicit")
        if route.type in allowed:
            ctx.route = route
            return None

        if pol.routing_value("on_private_external_request", "block") == "reroute_local":
            local = pol.default_local_model(agent)
            if local is not None:
                ctx.route = pol.route_for(local, allowed, router="reroute", rerouted_from=model)
                return Verdict.allow("route.private_external", f"rerouted {model} to local",
                                     owasp=OWASP, detail={"rerouted_from": model})
        return Verdict.block(
            "route.private_external",
            f"{ctx.session.data_class} data must not be sent to external model {model!r}; use a local model or 'auto'",
            code="PRIVATE_DATA_EXTERNAL_MODEL", owasp=OWASP)


@register
class RouteModelControl(Control):
    id = "route.model"
    phases = ("pre",)

    def evaluate(self, ctx, phase):
        req = ctx.request
        if req.kind != "model" or (req.model or "auto") != "auto" or ctx.route is None:
            return None
        allowed = ctx.route.allowed_types
        pol = ctx.policy
        external = pol.first_model_of_type("external")
        if len(allowed) < 2 or external is None:
            return None
        available = tuple(t for t in ("local", "external") if t in allowed)
        meta = RouteMeta(
            data_class=ctx.session.data_class, task_type="chat",
            size_chars=len(req.prompt_text), available=available,
            budget_remaining_pct=ctx.services.meter.external_remaining_pct(req.agent_id, pol),
        )
        try:
            choice = ctx.services.router.choose(meta, list(allowed))
        except Exception:  # fail closed: stay local
            choice = RouteChoice("local", "fail_closed")
        if choice.provider_type == "external" and "external" in allowed:
            ctx.route = pol.route_for(external, allowed, router=choice.router)
        else:
            ctx.route.router = choice.router
        return None
