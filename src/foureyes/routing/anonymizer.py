from __future__ import annotations

from typing import Protocol


class Anonymizer(Protocol):
    def process(self, provider_type: str) -> dict: ...


class NoOpAnonymizer:
    """Extension point: anonymization is not implemented; we only record that data went external."""

    def process(self, provider_type: str) -> dict:
        return {"anonymization": "not_applied" if provider_type == "external" else "n/a",
                "provider": provider_type}
