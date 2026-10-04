from __future__ import annotations

from pydantic import ValidationError

from foureyes.semantic.decision_model_types import decision_model_errors

from .catalog import ALLOWED_MODES, BASELINE_IDS, CATALOG_IDS
from .models import Policy


class PolicyError(ValueError):
    pass


def validate(raw: object) -> Policy:
    if not isinstance(raw, dict):
        raise PolicyError("schema error: policy must be a YAML mapping")
    try:
        policy = Policy.model_validate(raw)
    except ValidationError as exc:
        first = exc.errors()[0]
        raise PolicyError(f"schema error at {'.'.join(map(str, first['loc']))}: {first['msg']}") from exc

    for cid, cfg in policy.controls.items():
        if cid not in CATALOG_IDS:
            raise PolicyError(f"unknown control {cid!r}")
        mode = cfg.get("mode")
        if mode is not None and mode not in ALLOWED_MODES:
            raise PolicyError(f"control {cid}: invalid mode {mode!r}")
    for cid in BASELINE_IDS:
        if cid not in policy.controls:
            raise PolicyError(f"{cid} is a baseline control and cannot be removed")
        if policy.controls[cid].get("mode", "enforce") != "enforce":
            raise PolicyError(f"{cid} is a baseline control and must stay in enforce mode")

    order = policy.data_classes.get("order") or []
    allowed = policy.data_classes.get("allowed_upstream_types") or {}
    if not order or set(allowed) != set(order):
        raise PolicyError("data_classes.order and allowed_upstream_types must list the same classes")
    for i, cls in enumerate(order):
        if "local" not in allowed[cls]:
            raise PolicyError(f"data class {cls}: local upstream must always be allowed")
        if i > 0 and "external" in allowed[cls]:
            raise PolicyError(f"private data class {cls} must not allow external upstream")

    default_class = policy.sources.get("default_class", order[-1])
    if default_class not in order:
        raise PolicyError(f"sources.default_class: unknown class {default_class!r}")
    for ident, entry in policy.sources.items():
        if ident == "default_class":
            continue
        if not isinstance(entry, dict) or entry.get("class") not in order:
            raise PolicyError(f"source {ident}: unknown class {entry!r}")

    if policy.routing.get("on_private_external_request", "block") not in ("block", "reroute_local"):
        raise PolicyError("routing.on_private_external_request must be block or reroute_local")

    allowlist = (policy.models or {}).get("allowlist", {})
    for name, cfg in policy.agents.items():
        dm = cfg.get("default_model")
        if dm is not None and dm not in allowlist:
            raise PolicyError(f"agent {name}: default_model {dm!r} is not in models.allowlist")
    dm_errors = decision_model_errors(policy.decision_models, policy.controls, order)
    if dm_errors:
        raise PolicyError(dm_errors[0])
    return policy
