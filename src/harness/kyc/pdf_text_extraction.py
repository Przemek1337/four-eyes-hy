from __future__ import annotations

import io

MAX_PAGES = 50
MAX_TEXT_CHARS = 200_000  # like the text-attachment limit; bounds the number of decision model calls per document


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
        if len(reader.pages) > MAX_PAGES:
            raise PdfTextUnavailable(f"the PDF has {len(reader.pages)} pages; more than {MAX_PAGES} pages "
                                     "is not accepted")
        parts: list[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
            if sum(map(len, parts)) + len(parts) - 1 > MAX_TEXT_CHARS:  # stop reading as soon as it is too long
                raise PdfTextUnavailable(f"the PDF has more than {MAX_TEXT_CHARS} characters of text; "
                                         "split it into smaller documents")
        text = "\n".join(parts)
    except PdfTextUnavailable:
        raise
    except Exception as exc:
        raise PdfTextUnavailable(f"unreadable PDF: {exc}") from exc
    if not text.strip():
        raise PdfTextUnavailable("the PDF has no text layer")
    return text
