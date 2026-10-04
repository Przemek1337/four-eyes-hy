from .demo_environment import ScenarioResult, expected_final_status, run_document, tool_decisions

NAME = "clean_registry_extract"


def run(env) -> ScenarioResult:
    out = run_document(env, "nordwind-krs-clean", "krs", "0099000001")
    labels = out["session"]["labels"]
    return (ScenarioResult(NAME)
            .check("status", expected_final_status(env), out["status"])
            .check("client document marks the session untrusted", True, "untrusted" in labels)
            .check("no high_risk", False, "high_risk" in labels)
            .check("registry checked", "ALLOW", tool_decisions(out["events"]).get("public_registry_lookup", {}).get("decision")))
