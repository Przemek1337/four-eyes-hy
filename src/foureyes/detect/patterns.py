from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    kind: str


def _pesel_ok(s: str) -> bool:
    weights = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
    return (10 - sum(int(d) * w for d, w in zip(s, weights)) % 10) % 10 == int(s[10])


# 11 digits, optionally written as 6+5 or 2+2+2+5 with a space or hyphen (how people type it). The checksum
# keeps order numbers and phone numbers out.
_PESEL = re.compile(r"(?<!\d)\d{2}[ -]?\d{2}[ -]?\d{2}[ -]?\d{5}(?!\d)")


def find_pesel(text: str) -> list[Span]:
    return [Span(m.start(), m.end(), "pesel")
            for m in _PESEL.finditer(text) if _pesel_ok(re.sub(r"\D", "", m.group()))]


_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b", re.I)
# A Polish account number is often written without the country code: 26 digits, grouped as 2+4x6 or solid.
_IBAN_PL_BARE = re.compile(r"(?<![\d\w])\d{2}(?:[ -]?\d{4}){6}(?!\d)")


def _iban_ok(s: str) -> bool:
    s = s.replace(" ", "")
    if not 15 <= len(s) <= 34:
        return False
    return int("".join(str(int(c, 36)) for c in s[4:] + s[:4])) % 97 == 1


def find_iban(text: str) -> list[Span]:
    spans = []
    for m in _IBAN.finditer(text):
        candidate = m.group()
        while candidate:  # the optional tail group can swallow the next word: trim it until the checksum holds
            if _iban_ok(candidate.upper()):
                spans.append(Span(m.start(), m.start() + len(candidate), "iban"))
                break
            candidate = candidate.rsplit(" ", 1)[0] if " " in candidate else ""
    spans += [Span(m.start(), m.end(), "iban") for m in _IBAN_PL_BARE.finditer(text)
              if _iban_ok("PL" + re.sub(r"\D", "", m.group()))]
    return spans


def find_passport(text: str) -> list[Span]:
    return [Span(m.start(), m.end(), "passport") for m in re.finditer(r"\b[A-Za-z]{2}\d{7}\b", text)]


_SECRET_PATTERNS = [re.compile(p) for p in (
    r"sk-[A-Za-z0-9_\-]{16,}",
    r"AKIA[0-9A-Z]{16}",
    r"ghp_[A-Za-z0-9]{30,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S{6,}",
    r"Bearer [A-Za-z0-9._\-]{20,}",
    r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}",            # Stripe
    r"\bxox[abprs]-[A-Za-z0-9-]{10,}",                    # Slack
    r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}",  # JWT
    r"\bAIza[0-9A-Za-z_\-]{35}",                          # Google API key
    r"\bgithub_pat_[A-Za-z0-9_]{30,}", r"\bglpat-[A-Za-z0-9_\-]{20,}",
)]


def find_secrets(text: str) -> list[Span]:
    return [Span(m.start(), m.end(), "secret") for rx in _SECRET_PATTERNS for m in rx.finditer(text)]


DETECTORS: dict[str, Callable[[str], list[Span]]] = {
    "pesel": find_pesel, "iban": find_iban, "passport": find_passport, "secrets": find_secrets,
}


def find_all(text: str, names) -> list[Span]:
    spans: list[Span] = []
    for n in names:
        spans.extend(DETECTORS[n](text))
    return spans


def redact_text(text: str, names, token: str = "[REDACTED]") -> tuple[str, int]:
    spans = sorted(find_all(text, names), key=lambda s: (s.start, -s.end))
    merged: list[list[int]] = []
    for s in spans:
        if merged and s.start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], s.end)
        else:
            merged.append([s.start, s.end])
    for a, b in reversed(merged):
        text = text[:a] + token + text[b:]
    return text, len(merged)


def redact_obj(obj: Any, names, token: str = "[REDACTED]") -> tuple[Any, int]:
    if isinstance(obj, str):
        return redact_text(obj, names, token)
    if isinstance(obj, dict):
        out, total = {}, 0
        for k, v in obj.items():
            out[k], n = redact_obj(v, names, token)
            total += n
        return out, total
    if isinstance(obj, list):
        items, total = [], 0
        for v in obj:
            nv, n = redact_obj(v, names, token)
            items.append(nv)
            total += n
        return items, total
    return obj, 0


def drop_keys(obj: Any, keys) -> tuple[Any, int]:
    keys = set(keys)
    if isinstance(obj, dict):
        out, total = {}, 0
        for k, v in obj.items():
            if k in keys:
                total += 1
                continue
            out[k], n = drop_keys(v, keys)
            total += n
        return out, total
    if isinstance(obj, list):
        items, total = [], 0
        for v in obj:
            nv, n = drop_keys(v, keys)
            items.append(nv)
            total += n
        return items, total
    return obj, 0
