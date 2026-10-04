from __future__ import annotations

import json
from typing import Protocol


class RegistryRecordNotFound(LookupError):
    pass


class RegistryUnavailable(RuntimeError):
    pass


class RegistryLookup(Protocol):
    registry: str
    live: bool

    def lookup(self, number: str) -> dict: ...

    def summarize(self, record: dict) -> dict: ...


def lookup_result(registry: RegistryLookup, number: str) -> dict:
    """Tool-shaped answer that never raises, so the agent (and the audit) see exactly what happened."""
    base = {"registry": registry.registry, "number": number}
    try:
        record = registry.lookup(number)
    except json.JSONDecodeError:
        return {**base, "status": "unavailable", "error": "unreadable record"}
    except ValueError as exc:
        return {**base, "status": "invalid_number", "error": str(exc)}
    except RegistryRecordNotFound:
        return {**base, "status": "not_found"}
    except RegistryUnavailable as exc:
        return {**base, "status": "unavailable", "error": str(exc)}
    try:
        company = registry.summarize(record)
    except (KeyError, TypeError) as exc:
        return {**base, "status": "unavailable", "error": f"unexpected record shape: {exc!r}"}
    return {**base, "status": "found", "source": "live" if registry.live else "file", "company": company}
