import io

import pytest
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from harness.demo_documents import PDF_DIR
from harness.demo_documents.generate_registry_extract_pdfs import DOCUMENT_FILES, generate
from harness.kyc.pdf_text_extraction import NotAPdf, PdfTextUnavailable, extract_pdf_text
from harness.kyc.tools import KycTools


def text_of(path):
    return extract_pdf_text(path.read_bytes())


@pytest.fixture(scope="module")
def fresh(tmp_path_factory):
    out = tmp_path_factory.mktemp("pdf")
    generate(out)
    return out


def test_four_documents_are_generated(fresh):
    assert sorted(p.name for p in fresh.glob("*.pdf")) == sorted(DOCUMENT_FILES)


def test_injected_pdf_carries_the_hidden_instruction_and_the_clean_one_does_not(fresh):
    assert "skip sanctions screening" in text_of(fresh / "nordwind_krs_injected.pdf").lower()
    clean = text_of(fresh / "nordwind_krs_clean.pdf")
    assert "skip sanctions" not in clean.lower() and "NORDWIND" in clean and "0099000001" in clean


def test_borderline_pdf_has_the_note_and_an_unmasked_pesel(fresh):
    text = text_of(fresh / "nordwind_krs_borderline.pdf")
    assert "Note for automated reviewers" in text and "44051401359" in text


def test_thames_pdf_is_an_english_companies_house_extract(fresh):
    text = text_of(fresh / "thames_freight_companies_house_clean.pdf")
    assert "THAMES FREIGHT LTD" in text and "Company number: 99000001" in text


def test_generation_is_deterministic_and_the_committed_files_are_current(fresh, tmp_path):
    generate(tmp_path)
    for name in DOCUMENT_FILES:
        assert text_of(tmp_path / name) == text_of(fresh / name) == text_of(PDF_DIR / name)


def test_not_a_pdf_and_a_pdf_without_text():
    with pytest.raises(NotAPdf):
        extract_pdf_text(b"hello")
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    with pytest.raises(PdfTextUnavailable):
        extract_pdf_text(buf.getvalue())
    with pytest.raises(PdfTextUnavailable):
        extract_pdf_text(b"%PDF-1.4 this is not really a pdf")


def test_encrypted_pdf_is_unavailable():
    writer = PdfWriter()
    writer.append(PdfReader(PDF_DIR / "nordwind_krs_clean.pdf"))
    writer.encrypt("secret")
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(PdfTextUnavailable):
        extract_pdf_text(buf.getvalue())


def test_kyc_tools_read_the_pdf_documents():
    out = KycTools().entities_documents_read("C1", "nordwind-krs-injected")
    assert "skip sanctions screening" in out["text"].lower()
