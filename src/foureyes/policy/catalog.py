CATALOG_IDS = (
    "auth.agent_key", "models.allowlist", "authz.tools", "authz.tool_schema", "authz.scope",
    "data.classify_net", "route.model", "flow.untrusted", "dlp.redact_inflight", "log.redact",
    "output.safe", "budget.session", "budget.spend", "sig.feed", "sem.prompt_injection",
    "sem.action_judge",
)
SINK_IDS = frozenset({"log.redact"})        # handled by AuditSink, not by the pipeline
BASELINE_IDS = frozenset({"auth.agent_key"})  # defined in code on purpose
ALLOWED_MODES = frozenset({"enforce", "monitor", "redact", "block"})
