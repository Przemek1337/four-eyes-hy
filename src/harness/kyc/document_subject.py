"""Read the subject of a registry extract, without treating document instructions as authority."""
from __future__ import annotations

import re
import unicodedata


def folded(text: str) -> str:
    text = text.translate(str.maketrans({"ł": "l", "Ł": "L"}))
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def company_key(name: str) -> str:
    key = re.sub(r"[^a-z0-9]", "", folded(name).lower())
    return key.replace("spolkazograniczonaodpowiedzialnoscia", "spzoo").replace("spolkaakcyjna", "sa")


def document_subject(text: str) -> dict | None:
    # Only the extract header identifies the subject; later pages may mention other companies.
    header = folded(text[:6000])
    krs = re.search(r"\bNumer KRS\s*:\s*([0-9]{10})\b", header, re.I)
    if krs:
        # Official KRS printouts put field values on the following line; demo extracts use Firma:.
        name = re.search(r"(?:3\.\s*Firma, pod ktora spolka dziala|Firma\s*:)\s*\n?([^\n]+)", header, re.I)
        if not name:
            return None
        # Find the equivalent span in the original text to preserve Polish spelling.
        original_lines = text[:6000].splitlines()
        legal_name = next((line.strip() for line in original_lines if folded(line).strip() == name[1].strip()), None)
        if legal_name is None:
            legal_name = next((line.split(":", 1)[1].strip() for line in original_lines
                               if folded(line).strip().lower().startswith("firma:")), name[1].strip())
        form = re.search(r"(?:1\.\s*Oznaczenie formy prawnej|Forma prawna\s*:)\s*\n?([^\n]+)", header, re.I)
        legal_form = folded(form[1] if form else legal_name).upper()
        structure = ("sp_zoo" if "OGRANICZONA ODPOWIEDZIALNOSCIA" in legal_form
                     else "sa" if "SPOLKA AKCYJNA" in legal_form else None)
        return {"legalName": legal_name, "legalStructure": structure, "country": "PL",
                "registry": "krs", "registryNumber": krs[1]}
    number = re.search(r"\bCompany number\s*:\s*([A-Z0-9]{8})\b", header, re.I)
    name = re.search(r"\bCompany name\s*:\s*([^\n]+)", text[:6000], re.I)
    if number and name:
        return {"legalName": name[1].strip(), "legalStructure": "ltd" if re.search(
            r"Company type\s*:\s*Private limited company", header, re.I) else None,
                "country": "GB", "registry": "companies_house", "registryNumber": number[1].upper()}
    return None
