from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx

from .registry_lookup_port import RegistryRecordNotFound, RegistryUnavailable

LIVE_URL = "https://api.company-information.service.gov.uk/company/{number}"


class CompaniesHouseRegistryLookup:
    """UK Companies House. Files by default; the public data API when CH_API_KEY is set (HTTP Basic, key as user)."""

    registry = "companies_house"

    def __init__(self, extracts_dir: Path, api_key: str | None = None, client: httpx.Client | None = None):
        self.extracts_dir = Path(extracts_dir)
        self.api_key = api_key
        self.live = bool(api_key)
        self.client = client or httpx.Client(timeout=10.0)

    @classmethod
    def from_env(cls, extracts_dir: Path, client: httpx.Client | None = None) -> "CompaniesHouseRegistryLookup":
        return cls(extracts_dir, api_key=os.environ.get("CH_API_KEY") or None, client=client)

    def lookup(self, number: str) -> dict:
        if not re.fullmatch(r"[A-Z0-9]{8}", number or "", re.ASCII):
            raise ValueError("a Companies House number has 8 characters")
        if self.live:
            return self._live(number)
        path = self.extracts_dir / f"companies_house_{number}.json"
        if not path.exists():
            raise RegistryRecordNotFound(number)
        return json.loads(path.read_text(encoding="utf-8"))

    def _live(self, number: str) -> dict:
        try:
            resp = self.client.get(LIVE_URL.format(number=number), auth=(self.api_key, ""))
        except httpx.HTTPError as exc:
            raise RegistryUnavailable(str(exc)) from exc
        if resp.status_code == 404:
            raise RegistryRecordNotFound(number)
        if resp.status_code != 200:
            raise RegistryUnavailable(f"Companies House answered {resp.status_code}")
        try:
            return resp.json()
        except ValueError as exc:
            raise RegistryUnavailable("unreadable answer") from exc

    def summarize(self, record: dict) -> dict:
        return {"legalName": record["company_name"], "legalStructure": record.get("type", "other"), "country": "GB",
                "registryStatus": record.get("company_status"), "registryNumber": record["company_number"]}
