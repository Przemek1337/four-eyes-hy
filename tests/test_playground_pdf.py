import base64
import io

from reportlab.pdfgen import canvas

from harness.demo_documents import PDF_DIR
from harness.kyc.runner import make_document_runner
from helpers import KYC_PHRASES, kyc_gateway


def playground(tmp_path):
    gw = kyc_gateway(tmp_path)
    gw.services.document_runner = make_document_runner(gw.client, gw.kyc, "k-kyc")
    return gw.client


def pdf_body(name, data=None):
    data = data if data is not None else (PDF_DIR / name).read_bytes()
    return {"mode": "document", "text": "",
            "file": {"name": name, "content_type": "application/pdf", "content_base64": base64.b64encode(data).decode()}}


def blank_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    return buf.getvalue()


def test_injected_pdf_dropped_in_the_playground_is_stopped_and_held(tmp_path):
    body = playground(tmp_path).post("/admin/chat", json=pdf_body("nordwind_krs_injected.pdf")).json()
    assert body["decision"] == "APPROVAL" and body["message"] == "awaiting_approval"
    assert [(s["tool"], s["code"]) for s in body["steps"]][1:] == [("entities_submit", "TOOL_ORDER"),
                                                                   ("send_email", "APPROVAL_REQUIRED")]
    assert body["data_class"] == "bank_secret"


def test_clean_pdf_follows_the_normal_flow(tmp_path):
    body = playground(tmp_path).post("/admin/chat", json=pdf_body("nordwind_krs_clean.pdf")).json()
    assert body["message"] == "awaiting_approval"  # strict profile: a human signs the submission
    assert all(s["code"] != "TOOL_ORDER" for s in body["steps"])


def test_files_that_are_not_readable_pdfs_are_explained(tmp_path):
    client = playground(tmp_path)
    r = client.post("/admin/chat", json=pdf_body("fake.pdf", b"hello, I am text"))
    assert r.status_code == 422 and "not a PDF" in r.json()["error"]["message"]
    r = client.post("/admin/chat", json=pdf_body("blank.pdf", blank_pdf()))
    assert r.status_code == 422 and "no text layer" in r.json()["error"]["message"]


def test_bad_base64_and_too_big(tmp_path):
    client = playground(tmp_path)
    bad = {"mode": "document", "text": "", "file": {"name": "x.pdf", "content_type": "application/pdf",
                                                    "content_base64": "%%% not base64"}}
    assert client.post("/admin/chat", json=bad).status_code == 400
    big = pdf_body("big.pdf", b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024))
    assert client.post("/admin/chat", json=big).status_code == 413


def test_pasted_text_documents_still_work(tmp_path):
    body = playground(tmp_path).post("/admin/chat", json={"mode": "document", "text": "Note. " + KYC_PHRASES[0]}).json()
    assert body["steps"] and body["session_id"]
