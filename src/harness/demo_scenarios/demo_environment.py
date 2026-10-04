from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

import httpx

from harness.kyc.agent import run_kyc_agent


@dataclass
class DemoEnvironment:
    gateway: httpx.Client          # base_url = the gateway (a FastAPI TestClient works too)
    kyc_key: str
    dev_key: str
    live_krs_number: str = "0099000001"
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:6])


@dataclass
class ScenarioResult:
    name: str
    checks: list[tuple[str, object, object]] = field(default_factory=list)

    def check(self, what: str, expected, actual) -> "ScenarioResult":
        self.checks.append((what, expected, actual))
        return self

    @property
    def ok(self) -> bool:
        return all(expected == actual for _, expected, actual in self.checks)


def policy_profile(env: DemoEnvironment) -> str:
    return env.gateway.get("/admin/policy").json()["profile"]


def expected_final_status(env: DemoEnvironment) -> str:
    return "complete" if policy_profile(env) == "relaxed" else "awaiting_approval"


def run_document(env: DemoEnvironment, document_id: str, registry: str, number: str, client_id: str = "C1",
                 task: str = "KYC onboarding for Nordwind Sp. z o.o.") -> dict:
    """The KYC agent reads one PDF-backed client document through the gateway; returns what compliance sees."""
    session_id = f"demo-{document_id}-{env.run_id}"
    out = run_kyc_agent(env.gateway, key=env.kyc_key, session_id=session_id, document_id=document_id,
                        client_id=client_id, registry=registry, company_number=number, task=task)
    detail = env.gateway.get(f"/admin/sessions/{session_id}").json()
    return {"status": out["status"], "session": detail["session"], "events": detail["events"],
            "raw": json.dumps(detail, ensure_ascii=False)}


def tool_decisions(events: list[dict]) -> dict[str, dict]:
    return {e["resource"]: {"decision": e.get("decision"), "code": e.get("code")} for e in events
            if e.get("event", "decision") == "decision" and e.get("kind") == "tool"}


def mcp_call(env: DemoEnvironment, key: str, tool: str, args: dict, session: str, scope: str = "client_id=C1") -> dict:
    headers = {"Authorization": f"Bearer {key}", "X-FourEyes-Session": session, "X-FourEyes-Scope": scope,
               "X-FourEyes-Task": "KYC onboarding for Nordwind Sp. z o.o."}
    result = env.gateway.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                                             "params": {"name": tool, "arguments": args}}).json()["result"]
    content = result.get("structuredContent") or {}
    if result.get("isError"):
        return {"decision": content["error"]["decision"], "code": content["error"]["code"]}
    return {"decision": content["foureyes"]["decision"], "code": None}
