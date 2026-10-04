from __future__ import annotations

import uuid

from harness.company_registries.companies_house_registry_lookup import CompaniesHouseRegistryLookup
from harness.company_registries.krs_registry_lookup import KrsRegistryLookup
from harness.company_registries.registry_lookup_port import lookup_result
from harness.demo_documents import PDF_DIR, REGISTRY_EXTRACTS_DIR

from . import data
from .pdf_text_extraction import extract_pdf_text


class KycTools:
    """Mock tools modelled on a public bank onboarding API: create entity → documents → submit → status."""

    def __init__(self, registries: dict | None = None) -> None:
        self.registries = registries if registries is not None else {
            "krs": KrsRegistryLookup.from_env(REGISTRY_EXTRACTS_DIR),
            "companies_house": CompaniesHouseRegistryLookup.from_env(REGISTRY_EXTRACTS_DIR),
        }
        self.documents = dict(data.DOCUMENTS)
        self.clients = dict(data.CLIENTS)
        self.document_subjects: dict[str, dict] = {}
        self.document_owners: dict[str, str] = {}
        self.entities: dict[str, dict] = {}
        self.sent: list[dict] = []
        self.submitted: list[str] = []
        self.loaded_models: list[str] = []

    def handlers(self) -> dict:
        return {name: getattr(self, name) for name in (
            "entities_create", "entities_get", "entities_documents_read", "entities_submit", "sanctions_check",
            "send_email", "update_case_notes", "search_documents", "load_model", "public_registry_lookup", "uk_registry_lookup")}

    def schemas(self) -> dict:
        obj = lambda props, req=(): {"type": "object", "properties": props, "required": list(req)}  # noqa: E731
        s = {"type": "string"}
        return {
            "entities_create": obj({"legalName": s, "legalStructure": s, "country": s, "client_id": s},
                                   ("legalName", "legalStructure", "country")),
            "entities_get": obj({"client_id": s}, ("client_id",)),
            "entities_documents_read": obj({"client_id": s, "document_id": s}, ("client_id",)),
            "entities_submit": obj({"entity_id": s}, ("entity_id",)),
            "sanctions_check": obj({"name": s}, ("name",)),
            "send_email": obj({"to": s, "subject": s, "body": s}, ("to",)),
            "update_case_notes": obj({"note": s, "case_status": s}, ("note",)),
            "search_documents": obj({"query": s, "client_id": s}, ("query", "client_id")),
            "load_model": obj({"path": s, "source": s}, ("path",)),
            "public_registry_lookup": obj({"krs_number": s}, ("krs_number",)),
            "uk_registry_lookup": obj({"company_number": s}, ("company_number",)),
        }

    def entities_create(self, legalName, legalStructure, country, client_id=None):
        eid = f"E-{uuid.uuid4().hex[:6]}"
        self.entities[eid] = {"legalName": legalName, "legalStructure": legalStructure, "country": country,
                              "status": "DRAFT"}
        return {"entity_id": eid, "status": "DRAFT"}

    def entities_get(self, client_id):
        client = self.clients[client_id]
        director = data.DIRECTORS.get(client_id, {})
        return {"client_id": client_id, "legalName": client["legalName"],
                **({"director": director["name"]} if "name" in director else {}),
                **{k: director[k] for k in ("pesel", "passport_no", "iban") if k in director}}

    def register_upload(self, text: str, subject: dict | None) -> tuple[str, str]:
        doc_id = f"upload-{uuid.uuid4().hex}"
        client_id = f"client-{uuid.uuid4().hex}"
        self.documents[doc_id] = text
        self.document_owners[doc_id] = client_id
        if subject:
            self.document_subjects[doc_id] = dict(subject)
            self.clients[client_id] = dict(subject)
        return doc_id, client_id

    def entities_documents_read(self, client_id, document_id="nordwind-clean"):
        if document_id in self.document_owners and self.document_owners[document_id] != client_id:
            raise ValueError("this document belongs to another client")
        if document_id not in self.documents and document_id in data.PDF_DOCUMENTS:
            self.documents[document_id] = extract_pdf_text((PDF_DIR / data.PDF_DOCUMENTS[document_id]).read_bytes())
        if document_id not in self.documents:
            raise ValueError("unknown document")
        return {"document_id": document_id, "text": self.documents[document_id],
                **({"subject": self.document_subjects[document_id]} if document_id in self.document_subjects else {})}

    def entities_submit(self, entity_id):
        self.submitted.append(entity_id)
        return {"entity_id": entity_id, "status": "REVIEW"}

    def sanctions_check(self, name):
        return {"name": name, "result": "clear"}

    def send_email(self, to, subject="", body=""):
        self.sent.append({"to": to, "subject": subject, "body": body})
        return {"sent": True}

    def update_case_notes(self, note, case_status=None):
        return {"ok": True}

    def search_documents(self, query, client_id):
        return {"results": [dict(r) for r in data.INDEX]}

    def load_model(self, path, source=None):
        self.loaded_models.append(path)
        return {"loaded": True}

    def public_registry_lookup(self, krs_number):
        return lookup_result(self.registries["krs"], krs_number)

    def uk_registry_lookup(self, company_number):
        return lookup_result(self.registries["companies_house"], company_number)
