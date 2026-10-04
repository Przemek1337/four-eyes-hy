from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx

from .registry_lookup_port import RegistryRecordNotFound, RegistryUnavailable

LIVE_URL = "https://api-krs.ms.gov.pl/api/krs/OdpisAktualny/{number}"
LEGAL_FORMS = {"SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ": "sp_zoo", "SPÓŁKA AKCYJNA": "sa"}


class KrsRegistryLookup:
    """Polish National Court Register. Files by default; the public API (no key) only with KRS_LIVE=1."""

    registry = "krs"

    def __init__(self, extracts_dir: Path, live: bool = False, client: httpx.Client | None = None):
        self.extracts_dir = Path(extracts_dir)
        self.live = live
        self.client = client or httpx.Client(timeout=10.0)

    @classmethod
    def from_env(cls, extracts_dir: Path, client: httpx.Client | None = None) -> "KrsRegistryLookup":
        return cls(extracts_dir, live=os.environ.get("KRS_LIVE") == "1", client=client)

    def lookup(self, number: str) -> dict:
        if not re.fullmatch(r"[0-9]{10}", number or ""):
            raise ValueError("a KRS number has 10 digits")
        if self.live:
            return self._live(number)
        path = self.extracts_dir / f"krs_{number}.json"
        if not path.exists():
            raise RegistryRecordNotFound(number)
        return json.loads(path.read_text(encoding="utf-8"))

    def _live(self, number: str) -> dict:
        try:
            resp = self.client.get(LIVE_URL.format(number=number), params={"rejestr": "P", "format": "json"})
        except httpx.HTTPError as exc:
            raise RegistryUnavailable(str(exc)) from exc
        if resp.status_code == 404:
            raise RegistryRecordNotFound(number)
        if resp.status_code != 200:
            raise RegistryUnavailable(f"KRS API answered {resp.status_code}")
        try:
            return resp.json()
        except ValueError as exc:
            raise RegistryUnavailable("unreadable answer") from exc

    def summarize(self, record: dict) -> dict:
        odpis = record["odpis"]
        entity = odpis["dane"]["dzial1"]["danePodmiotu"]
        return {"legalName": entity["nazwa"],
                "legalStructure": LEGAL_FORMS.get(entity.get("formaPrawna", "").upper(), "other"),
                "country": "PL", "registryStatus": "registered", "registryNumber": odpis["naglowekA"]["numerKRS"],
                "nip": (entity.get("identyfikatory") or {}).get("nip")}
