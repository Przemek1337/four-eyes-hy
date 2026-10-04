from __future__ import annotations

import uuid

from .agent import run_kyc_agent


def make_document_runner(client, tools, key: str):
    """Judges' chat, Document mode: the pasted text becomes a client upload and a KYC agent session starts."""
    def run(text: str, session_id: str) -> dict:
        doc_id = f"upload-{uuid.uuid4().hex[:6]}"
        tools.documents[doc_id] = text
        out = run_kyc_agent(client, key=key, session_id=session_id, document_id=doc_id)
        last = next((s for s in reversed(out["steps"]) if s["outcome"] in ("BLOCK", "APPROVAL")), None)
        sess = client.get(f"/admin/sessions/{session_id}").json()
        decision = last["outcome"] if last else "ALLOW"
        return {"session_id": session_id, "decision": decision, "rule": None, "layer": None,
                "code": last["code"] if last else None, "owasp": [], "data_class": sess["session"]["data_class"],
                "route": None, "latency_ms": None, "injection_score": None, "reply": out["reply"],
                "approval_id": last["approval_id"] if last else None,
                "message": out["status"], "steps": out["steps"]}
    return run
