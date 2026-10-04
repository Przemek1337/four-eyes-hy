from .demo_environment import ScenarioResult, mcp_call

NAME = "developer_without_access"
SECRET_PROMPT = "Klient Nordwind ma przyznany limit 2 mln zł, wewnętrzny rating B-, trwa restrukturyzacja – streść to."


def run(env) -> ScenarioResult:
    s = lambda n: f"dev-{n}-{env.run_id}"  # noqa: E731 - fresh sessions on every run
    res = ScenarioResult(NAME)
    res.check("1 public registry lookup", "ALLOW",
              mcp_call(env, env.dev_key, "public_registry_lookup", {"krs_number": env.live_krs_number}, s(1), scope="")["decision"])
    res.check("2 client data", "TOOL_NOT_ALLOWED",
              mcp_call(env, env.dev_key, "entities_get", {"client_id": "C1"}, s(2))["code"])
    res.check("3 client documents", "TOOL_NOT_ALLOWED",
              mcp_call(env, env.dev_key, "entities_documents_read", {"client_id": "C1"}, s(3))["code"])
    res.check("4 wrong key", "AUTH_FAILED",
              mcp_call(env, "not-a-key", "public_registry_lookup", {"krs_number": "0099000001"}, s(4))["code"])
    r5 = env.gateway.post("/v1/chat/completions",
                          headers={"Authorization": f"Bearer {env.dev_key}", "X-FourEyes-Session": s(5)},
                          json={"model": "ext-gpt-sim", "messages": [{"role": "user", "content": SECRET_PROMPT}]})
    res.check("5 bank secret to an external model", "PRIVATE_DATA_EXTERNAL_MODEL", (r5.json().get("error") or {}).get("code"))
    res.check("6 another client's documents", "SCOPE_VIOLATION",
              mcp_call(env, env.kyc_key, "search_documents", {"query": "statements", "client_id": "C2"}, s(6))["code"])
    return res
