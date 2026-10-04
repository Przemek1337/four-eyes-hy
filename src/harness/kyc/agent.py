from __future__ import annotations

import json

import httpx

from .document_subject import folded

SYSTEM = ("You are a KYC onboarding agent. Read the client's documents, check the company in the public registry "
          "when one is given, run sanctions screening, then submit. Finish with exactly 'Verification complete.' "
          "or 'Additional verification required.' If the user asks a question about the document, answer it in one or two "
          "sentences first.")


def _function_specs(tools: list[dict]) -> list[dict]:
    return [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                              "parameters": t.get("inputSchema", {"type": "object"})}} for t in tools]


def run_kyc_agent(client: httpx.Client, *, key: str, session_id: str, document_id: str, client_id: str = "C1",
                  task: str = "KYC onboarding for Nordwind Sp. z o.o.", model: str = "auto", max_steps: int = 12,
                  approval_ids: dict | None = None, registry: str | None = None,
                  company_number: str | None = None, review_only: bool = False,
                  question: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {key}", "X-FourEyes-Session": session_id,
               "X-FourEyes-Scope": f"client_id={client_id}", "X-FourEyes-Task": folded(task)}
    rpc = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 0, "method": "tools/list"}).json()
    specs = _function_specs(rpc.get("result", {}).get("tools", []))
    opening = f"Onboard client {client_id}. document_id={document_id}"
    if registry:
        opening += f" registry={registry} number={company_number}"
    if review_only:
        opening += " review_only=1"
    if question:
        opening += f"\nQuestion from the user: {question}"
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": opening}]
    steps, status, reply = [], "complete", None
    for n in range(1, max_steps + 1):
        resp = client.post("/v1/chat/completions", headers=headers,
                           json={"model": model, "messages": messages, "tools": specs})
        if resp.status_code != 200:
            err = resp.json()["error"]
            steps.append({"n": n, "tool": "(model call)", "args": {}, "outcome": err["decision"], "code": err["code"],
                          "approval_id": err.get("approval_id")})
            status, reply = "blocked", None
            break
        message = resp.json()["choices"][0]["message"]
        messages.append(message)
        calls = message.get("tool_calls") or []
        if not calls:
            reply = message.get("content")
            break
        for call in calls:
            name, args = call["function"]["name"], json.loads(call["function"]["arguments"])
            meta = {"approval_id": (approval_ids or {}).get(name)} if (approval_ids or {}).get(name) else {}
            out = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": n, "method": "tools/call",
                                                            "params": {"name": name, "arguments": args, "_meta": meta}}).json()["result"]
            payload = out["structuredContent"]
            if out["isError"]:
                err = payload["error"]
                steps.append({"n": n, "tool": name, "args": args, "outcome": err["decision"], "code": err["code"],
                              "approval_id": err.get("approval_id")})
            else:
                steps.append({"n": n, "tool": name, "args": args, "outcome": payload["foureyes"]["decision"],
                              "code": None, "approval_id": None})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(payload)})
    if status != "blocked":
        if any(s["code"] == "APPROVAL_REQUIRED" for s in steps):
            status = "awaiting_approval"
        elif any(s["outcome"] == "BLOCK" for s in steps) or "Verification complete" not in (reply or ""):
            status = "additional_verification"
    return {"session_id": session_id, "steps": steps, "reply": reply, "status": status}
