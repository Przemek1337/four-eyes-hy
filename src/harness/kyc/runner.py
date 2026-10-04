from __future__ import annotations

from .agent import run_kyc_agent
from .document_subject import document_subject
from .pdf_text_extraction import extract_pdf_text


def make_document_runner(client, tools, key: str):
    """Judges' chat, Document mode: the pasted text becomes a client upload and a KYC agent session starts."""
    def run(text: str, session_id: str, pdf: bytes | None = None, question: str | None = None) -> dict:
        if pdf is not None:
            text = extract_pdf_text(pdf)  # raises NotAPdf / PdfTextUnavailable (ValueError) -> 422
        subject = document_subject(text)
        doc_id, client_id = tools.register_upload(text, subject)
        task = f"KYC onboarding for {subject['legalName']}" if subject else "Review an unidentified client document"
        out = run_kyc_agent(client, key=key, session_id=session_id, document_id=doc_id, client_id=client_id,
                            task=task, registry=subject["registry"] if subject else None,
                            company_number=subject["registryNumber"] if subject else None,
                            review_only=subject is None or subject["legalStructure"] is None, question=question)
        last = next((s for s in reversed(out["steps"]) if s["outcome"] in ("BLOCK", "APPROVAL")), None)
        sess = client.get(f"/admin/sessions/{session_id}").json()
        # A successful document read is not a clean security verdict. Carry the
        # document findings separately from decisions about individual operations.
        findings = []
        document_event = None
        for event in sess.get("events", []):
            if event.get("resource") == "entities_documents_read":
                document_event = event
            for alert in event.get("alerts", []):
                if alert.get("kind", "").startswith("document."):
                    findings.append({**alert, "rule": "sig.feed" if alert["kind"] == "document.signature"
                                     else "sem.prompt_injection",
                                     "layer": "det" if alert["kind"] == "document.signature" else "ai"})
        detected = any(f["kind"] == "document.signature" or
                       (f["kind"] == "document.injection" and not f.get("error")) for f in findings)
        # the model that really handled the agent's last call, as the gateway recorded it
        used = next((e["route"] for e in reversed(sess.get("events", [])) if e.get("kind") == "model" and e.get("route")), None)
        route = ({"type": used["chosen"], "model": used["model"], "served_model": used.get("served_model"),
                  "router": used["router"], "rerouted_from": used["rerouted_from"]} if used else None)
        decision = last["outcome"] if last else "APPROVAL" if out["status"] == "additional_verification" else "ALLOW"
        reply = out["reply"]
        if subject:
            reply = f"Document subject: {subject['legalName']} ({subject['registry'].upper()} {subject['registryNumber']}). " + (reply or out["status"])
        return {"session_id": session_id, "decision": decision, "rule": None, "layer": None,
                "code": last["code"] if last else None, "owasp": [], "data_class": sess["session"]["data_class"],
                "route": route, "latency_ms": None,
                "injection_score": (document_event or {}).get("injection_score"),
                "ai": (document_event or {}).get("ai"), "reply": reply,
                "document_security": {"injection_detected": detected, "labels": sess["session"]["labels"],
                                      "findings": findings},
                "approval_id": last["approval_id"] if last else None,
                "message": out["status"], "steps": out["steps"]}
    return run
