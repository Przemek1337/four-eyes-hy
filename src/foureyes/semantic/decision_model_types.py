from __future__ import annotations

"""Static facts about decision model types and which control needs what. No imports from the rest of the core,
so the policy validator can use it without cycles."""

TYPE_CAPABILITIES: dict[str, frozenset[str]] = {
    "basal": frozenset({"yes_no", "choice"}),
    "granite_guardian": frozenset({"yes_no"}),
    "mock": frozenset({"yes_no", "choice"}),
    "jev": frozenset({"choice"}),  # external routing model; adapter not shipped
}
TYPE_BUILTIN_RULES: dict[str, frozenset[str]] = {
    "granite_guardian": frozenset({"jailbreak"}),
    "mock": frozenset({"jailbreak"}),
}
CONTROL_NEEDS = {"data.classify_net": "choice", "sem.prompt_injection": "yes_no", "sem.action_judge": "choice"}
LEGACY_MODELS = {"sem.prompt_injection": frozenset({"promptguard"}), "sem.action_judge": frozenset({"ollama"})}
TYPES_WITHOUT_ADAPTER = frozenset({"jev"})  # known to the router, but no client is shipped to ask it questions
BUILTIN_MODELS = {"mock": {"type": "mock", "location": "local"}}
LOCATIONS = ("local", "external")


def model_refs(controls: dict) -> dict[str, str]:
    refs: dict[str, str] = {}
    for cid, cfg in (controls or {}).items():
        cfg = cfg or {}
        name = (cfg.get("ai") or {}).get("model") if cid == "data.classify_net" else cfg.get("model")
        if cid in CONTROL_NEEDS and name:
            refs[cid] = name
    return refs


def _all_models(decision_models: dict) -> dict:
    return {**BUILTIN_MODELS, **(decision_models or {})}


def _control_conf(controls: dict, cid: str) -> dict:
    cfg = (controls or {}).get(cid) or {}
    return (cfg.get("ai") or {}) if cid == "data.classify_net" else cfg


def _min_confidence_error(cid: str, conf: dict) -> str | None:
    value = conf.get("min_confidence")
    where = f"{cid}.ai" if cid == "data.classify_net" else cid
    if value is None:
        return f"{where}: min_confidence is required when a decision model is used"
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 1:
        return f"{where}: min_confidence must be a number above 0 and at most 1, got {value!r}"
    return None


def decision_model_errors(decision_models: dict, controls: dict, class_order: list[str]) -> list[str]:
    errors: list[str] = []
    models = _all_models(decision_models)
    for name, cfg in (decision_models or {}).items():
        if not isinstance(cfg, dict) or cfg.get("type") not in TYPE_CAPABILITIES:
            errors.append(f"decision_models.{name}: unknown decision model type {(cfg or {}).get('type')!r}")
        elif cfg.get("location") not in LOCATIONS:
            errors.append(f"decision_models.{name}: location must be local or external")
        elif cfg["type"] != "jev" and cfg["location"] == "local" and not cfg.get("base_url"):
            errors.append(f"decision_models.{name}: base_url is required")
    for cid, name in model_refs(controls).items():
        if name in LEGACY_MODELS.get(cid, ()):
            continue
        cfg = models.get(name)
        if not isinstance(cfg, dict) or cfg.get("type") not in TYPE_CAPABILITIES:
            errors.append(f"{cid}: unknown decision model {name!r}")
            continue
        if cfg.get("location") == "external":
            errors.append(f"{cid}: decision model {name!r} is external; controls that read content need a local model")
        if CONTROL_NEEDS[cid] not in TYPE_CAPABILITIES[cfg["type"]]:
            errors.append(f"{cid}: decision model {name!r} cannot answer {CONTROL_NEEDS[cid]} questions")
        if cfg["type"] in TYPES_WITHOUT_ADAPTER and cfg.get("location") != "external":
            errors.append(f"{cid}: decision model {name!r} has type {cfg['type']!r}, which has no adapter")
        conf_error = _min_confidence_error(cid, _control_conf(controls, cid))
        if conf_error:
            errors.append(conf_error)
    inj = (controls or {}).get("sem.prompt_injection") or {}
    if "sem.prompt_injection" in model_refs(controls) and inj.get("model") not in LEGACY_MODELS["sem.prompt_injection"]:
        if not inj.get("rules"):
            errors.append("sem.prompt_injection: rules are required when a decision model is used")
    judge = (controls or {}).get("sem.action_judge") or {}
    if "sem.action_judge" in model_refs(controls) and judge.get("model") not in LEGACY_MODELS["sem.action_judge"]:
        if set(judge.get("options") or {}) != {"consistent", "out_of_scope"}:
            errors.append("sem.action_judge: options must be exactly consistent and out_of_scope")
    ai = ((controls or {}).get("data.classify_net") or {}).get("ai") or {}
    if ai:
        if not ai.get("model"):
            errors.append("data.classify_net.ai: model is required when the ai block is set")
        unknown = [c for c in (ai.get("classes") or {}) if c not in class_order]
        if unknown or not ai.get("classes"):
            errors.append(f"data.classify_net.ai: unknown data class {unknown or '(none given)'}")
    return errors


def decision_model_warnings(decision_models: dict, controls: dict) -> list[str]:
    warnings: list[str] = []
    inj = (controls or {}).get("sem.prompt_injection") or {}
    name = inj.get("model")
    cfg = _all_models(decision_models).get(name) if name else None
    if isinstance(cfg, dict):
        builtin = TYPE_BUILTIN_RULES.get(cfg.get("type"), frozenset())
        for rule, criterion in (inj.get("rules") or {}).items():
            if criterion == "builtin" and rule not in builtin:
                warnings.append(f"rule.skipped: sem.prompt_injection rule {rule!r} is not built into {name}")
    return warnings
