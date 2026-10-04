from types import SimpleNamespace

import pytest

from foureyes.controls.route import RouteInvariant, RouteModelControl
from foureyes.core.types import Outcome
from foureyes.routing.anonymizer import NoOpAnonymizer
from foureyes.routing.router import RouteChoice, RoutingModel, RuleBasedRouter
from helpers import make_ctx, snapshot

CLASSES = ["public", "personal_data", "bank_secret"]


class FakeMeter:
    def external_remaining_pct(self, agent_id, snapshot):
        return 100.0


def ctx_for(model, data_class="public", overrides=None, router=None, **kw):
    services = SimpleNamespace(router=router or RuleBasedRouter(), meter=FakeMeter())
    return make_ctx(model=model, session_class=data_class, overrides=overrides, services=services,
                    messages=kw.get("messages", [{"role": "user", "content": "hi"}]))


def test_private_session_with_explicit_external_model_is_blocked():
    ctx = ctx_for("ext-gpt-sim", "personal_data")
    v = RouteInvariant().evaluate(ctx, "pre")
    assert v.outcome is Outcome.BLOCK and v.code == "PRIVATE_DATA_EXTERNAL_MODEL"
    assert v.owasp == ("LLM02:2026",)


def test_reroute_local_switch_rewrites_route_and_records_origin():
    ctx = ctx_for("ext-gpt-sim", "bank_secret", overrides={"routing": {"on_private_external_request": "reroute_local"}})
    v = RouteInvariant().evaluate(ctx, "pre")
    assert v.outcome is Outcome.ALLOW and ctx.route.type == "local" and ctx.route.rerouted_from == "ext-gpt-sim"


def test_public_session_may_use_external_explicitly():
    ctx = ctx_for("ext-gpt-sim", "public")
    assert RouteInvariant().evaluate(ctx, "pre") is None
    assert ctx.route.type == "external"


def test_unknown_model_blocked_even_without_allowlist_control():
    ctx = ctx_for("ghost")
    v = RouteInvariant().evaluate(ctx, "pre")
    assert v.outcome is Outcome.BLOCK and v.code == "MODEL_NOT_ALLOWED"


@pytest.mark.parametrize("data_class", CLASSES)
@pytest.mark.parametrize("model", ["auto", "basal-1.0-1.5B", "ext-gpt-sim"])
@pytest.mark.parametrize("mode", ["block", "reroute_local"])
def test_invariant_never_routes_private_data_to_external(data_class, model, mode):
    ctx = ctx_for(model, data_class, overrides={"routing": {"on_private_external_request": mode}})
    v = RouteInvariant().evaluate(ctx, "pre")
    if ctx.route is not None:
        assert ctx.route.type in ctx.policy.allowed_upstream_types(data_class)
        if data_class != "public":
            assert ctx.route.type == "local"
    else:
        assert v.outcome is Outcome.BLOCK


def test_auto_defaults_to_local_then_router_may_pick_external_for_public_large_prompts():
    big = [{"role": "user", "content": "x" * 5000}]
    ctx = ctx_for("auto", "public", messages=big)
    assert RouteInvariant().evaluate(ctx, "pre") is None and ctx.route.type == "local"
    RouteModelControl().evaluate(ctx, "pre")
    assert ctx.route.type == "external" and ctx.route.router == "rule_based"


def test_router_never_chooses_external_for_private_even_if_it_tries():
    class Greedy:
        name = "greedy"

        def choose(self, meta, allowed):
            return RouteChoice("external", "greedy")

    ctx = ctx_for("auto", "personal_data", router=Greedy())
    RouteInvariant().evaluate(ctx, "pre")
    RouteModelControl().evaluate(ctx, "pre")
    assert ctx.route.type == "local"


def test_router_failure_falls_back_to_local():
    class Broken:
        name = "broken"

        def choose(self, meta, allowed):
            raise RuntimeError("down")

    ctx = ctx_for("auto", "public", router=Broken(), messages=[{"role": "user", "content": "x" * 5000}])
    RouteInvariant().evaluate(ctx, "pre")
    RouteModelControl().evaluate(ctx, "pre")
    assert ctx.route.type == "local"


def test_router_receives_metadata_only():
    seen = {}

    class Spy:
        name = "spy"

        def choose(self, meta, allowed):
            seen["meta"] = meta
            return RouteChoice("local", "spy")

    secret = "SECRET-PROMPT-CONTENT"
    ctx = ctx_for("auto", "public", router=Spy(), messages=[{"role": "user", "content": secret}])
    RouteInvariant().evaluate(ctx, "pre")
    RouteModelControl().evaluate(ctx, "pre")
    assert secret not in repr(seen["meta"]) and seen["meta"].size_chars == len(secret)


def test_anonymizer_is_noop_but_records_external_use():
    assert NoOpAnonymizer().process("external") == {"anonymization": "not_applied", "provider": "external"}
    assert NoOpAnonymizer().process("local") == {"anonymization": "n/a", "provider": "local"}
