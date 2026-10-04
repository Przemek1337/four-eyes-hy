from __future__ import annotations

import uuid

from . import data


class KycTools:
    """Mock tools modelled on a public bank onboarding API: create entity → documents → submit → status."""

    def __init__(self) -> None:
        self.documents = dict(data.DOCUMENTS)
        self.entities: dict[str, dict] = {}
        self.sent: list[dict] = []
        self.submitted: list[str] = []
        self.loaded_models: list[str] = []

    def handlers(self) -> dict:
        return {name: getattr(self, name) for name in (
            "entities_create", "entities_get", "entities_documents_read", "entities_submit", "sanctions_check",
            "send_email", "update_case_notes", "search_documents", "load_model", "public_registry_lookup")}

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
            "public_registry_lookup": obj({"name": s}, ("name",)),
        }

    def entities_create(self, legalName, legalStructure, country, client_id=None):
        eid = f"E-{uuid.uuid4().hex[:6]}"
        self.entities[eid] = {"legalName": legalName, "legalStructure": legalStructure, "country": country,
                              "status": "DRAFT"}
        return {"entity_id": eid, "status": "DRAFT"}

    def entities_get(self, client_id):
        return {"client_id": client_id, "legalName": data.CASE["legalName"], "director": data.DIRECTOR["name"],
                "pesel": data.DIRECTOR["pesel"], "passport_no": data.DIRECTOR["passport_no"],
                "iban": data.DIRECTOR["iban"]}

    def entities_documents_read(self, client_id, document_id="nordwind-clean"):
        return {"document_id": document_id, "text": self.documents.get(document_id, data.CLEAN_DOC)}

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

    def public_registry_lookup(self, name):
        return {"name": name, "status": "active", "registry_number": "KRS-0000000000"}
