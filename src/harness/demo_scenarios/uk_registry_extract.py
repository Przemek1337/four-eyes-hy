from .demo_environment import ScenarioResult, expected_final_status, run_document, tool_decisions

NAME = "uk_registry_extract"


def run(env) -> ScenarioResult:
    out = run_document(env, "thames-freight-clean", "companies_house", "99000001", client_id="C4",
                       task="KYC onboarding for Thames Freight Ltd")
    return (ScenarioResult(NAME)
            .check("status", expected_final_status(env), out["status"])
            .check("UK registry checked", "ALLOW", tool_decisions(out["events"]).get("uk_registry_lookup", {}).get("decision")))
