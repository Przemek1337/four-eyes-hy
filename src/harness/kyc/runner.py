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
        decision = last["outcome"] if last else "APPROVAL" if out["status"] == "additional_verification" else "ALLOW"
        reply = out["reply"]
        if subject:
            reply = f"Document subject: {subject['legalName']} ({subject['registry'].upper()} {subject['registryNumber']}). " + (reply or out["status"])
        return {"session_id": session_id, "decision": decision, "rule": None, "layer": None,
                "code": last["code"] if last else None, "owasp": [], "data_class": sess["session"]["data_class"],
                "route": None, "latency_ms": None, "injection_score": None, "ai": None, "reply": reply,
                "approval_id": last["approval_id"] if last else None,
                "message": out["status"], "steps": out["steps"]}
    return run
