from .demo_environment import ScenarioResult, run_document

NAME = "borderline_registry_extract"
DIRECTOR_PESEL = "44051401359"


def run(env) -> ScenarioResult:
    out = run_document(env, "nordwind-krs-borderline", "krs", "0099000001")
    return (ScenarioResult(NAME)
            .check("status", "awaiting_approval", out["status"])
            .check("unsure model still marks high_risk", True, "high_risk" in out["session"]["labels"])
            .check("PESEL redacted in the audit", False, DIRECTOR_PESEL in out["raw"]))
