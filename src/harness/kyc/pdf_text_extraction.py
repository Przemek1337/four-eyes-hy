from __future__ import annotations

import io


class NotAPdf(ValueError):
    pass


class PdfTextUnavailable(ValueError):
    pass


def extract_pdf_text(data: bytes) -> str:
    """All text of the PDF's text layer, including white or microscopic text: that is exactly what an agent
    reading the document sees, so the gateway must see it too. Fails instead of returning an empty 'clean' text."""
    if not data.startswith(b"%PDF-"):
        raise NotAPdf("not a PDF file")
    from pypdf import PdfReader  # harness extra; imported lazily

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise PdfTextUnavailable("encrypted PDF")
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except PdfTextUnavailable:
        raise
    except Exception as exc:
        raise PdfTextUnavailable(f"unreadable PDF: {exc}") from exc
    if not text.strip():
        raise PdfTextUnavailable("the PDF has no text layer")
    return text
