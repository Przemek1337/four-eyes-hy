"""Undo common obfuscation before detection runs.

Attackers hide an instruction from a pattern or a classifier by changing how it is written, not what it says:
look-alike letters, zero-width characters, spacing, leetspeak, full-width forms, base64, ROT13. `variants` returns the
original text plus a few normalised readings of it; callers run their detector on every reading and keep the worst
result. Detection only: the text that reaches the model or the tool is never rewritten."""
from __future__ import annotations

import base64
import binascii
import codecs
import re
import unicodedata

_INVISIBLE = {chr(c) for c in (0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x2060, 0xFEFF, 0x00AD)}
# Cyrillic and Greek letters that look like Latin ones.
_CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "і": "i", "ј": "j", "х": "x", "у": "y", "ѕ": "s", "ԁ": "d",
    "ɡ": "g", "һ": "h", "ո": "n", "ν": "v", "ο": "o", "ρ": "p", "α": "a", "ε": "e", "ι": "i", "κ": "k", "τ": "t",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X",
})
_LEET = str.maketrans({"4": "a", "3": "e", "1": "i", "0": "o", "5": "s", "7": "t", "@": "a", "$": "s"})
_SPACED = re.compile(r"(?<!\w)(?:\w[ .\-_]){3,}\w(?!\w)")
_B64 = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{16,}={0,2}(?![A-Za-z0-9+/=])")
_MAX_B64_TOKENS = 8


def _canonical(text: str, invisible_as: str = "") -> str:
    """`invisible_as=""` glues text split by zero-width characters ("ig\u200bnore"); `" "` reads them as spaces
    ("ignore\u200bprevious"). Both are used because attackers do both."""
    out = unicodedata.normalize("NFKC", text)
    hidden = "".join(chr(ord(c) - 0xE0000) for c in out if 0xE0020 <= ord(c) <= 0xE007E)  # decode Unicode tag chars
    out = "".join(invisible_as if c in _INVISIBLE else c for c in out if not 0xE0000 <= ord(c) <= 0xE007F)
    return (out + " " + hidden).strip() if hidden else out


def _despace(text: str) -> str:
    return _SPACED.sub(lambda m: re.sub(r"[ .\-_]", "", m.group()), text)


def _delet(text: str) -> str:
    """Leetspeak: only inside words that mix letters and digits, so plain numbers stay numbers."""
    def fix(m: re.Match) -> str:
        w = m.group()
        return w.translate(_LEET) if re.search(r"[A-Za-z]", w) and re.search(r"[\d@$]", w) else w
    return re.sub(r"[\w@$]{4,}", fix, text)


def _printable(raw: bytes) -> str | None:
    try:
        s = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return s if s and sum(c.isprintable() or c.isspace() for c in s) / len(s) >= 0.95 else None


def _decoded_base64(text: str) -> list[str]:
    out: list[str] = []
    for m in list(_B64.finditer(text))[:_MAX_B64_TOKENS]:
        token = m.group()
        try:
            decoded = _printable(base64.b64decode(token + "=" * (-len(token) % 4), validate=True))
        except (binascii.Error, ValueError):
            continue
        if decoded and len(decoded) >= 8:
            out.append(decoded)
    return out


def variants(text: str, rot13: bool = True) -> list[str]:
    """`text` first, then each distinct normalised reading of it (at most a handful). A pattern matcher can afford
    every reading; a model-based scorer passes `rot13=False` unless the text itself mentions ROT13."""
    if not text:
        return [text]
    seen = {text}
    out = [text]

    def add(candidate: str) -> None:
        if candidate and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)

    canon = _canonical(text).translate(_CONFUSABLES)
    add(canon)
    if any(c in _INVISIBLE for c in text):
        add(_canonical(text, " ").translate(_CONFUSABLES))
    despaced = _despace(canon)
    add(despaced)
    add(_delet(despaced))
    if rot13:
        add(codecs.encode(canon, "rot13"))
    for decoded in _decoded_base64(canon):
        add(decoded)
        if rot13:
            add(codecs.encode(decoded, "rot13"))
    return out
