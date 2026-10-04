from __future__ import annotations

import io
import pickletools
import re
import zipfile
from urllib.parse import urlparse

_ZERO_WIDTH = {chr(c) for c in (0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x2060, 0xFEFF)}
_MD_URL = re.compile(r"!?\[[^\]]*\]\((?P<url>[^)\s]+)[^)]*\)")


def has_unicode_smuggling(text: str) -> bool:
    return any(0xE0000 <= ord(c) <= 0xE007F or c in _ZERO_WIDTH for c in text)


def hidden_text(text: str) -> str:
    """Decode Unicode tag characters (U+E0000 block) back to the ASCII they hide."""
    return "".join(chr(ord(c) - 0xE0000) for c in text if 0xE0020 <= ord(c) <= 0xE007E)


def _norm(module: str, name: str) -> str:
    return f"{'os' if module in ('posix', 'nt') else module}.{name}"


def _scan_stream(data: bytes) -> list[str]:
    found: list[str] = []
    strings: list[str] = []
    for op, arg, _ in pickletools.genops(data):
        if op.name in ("SHORT_BINUNICODE", "BINUNICODE", "UNICODE", "BINUNICODE8"):
            strings.append(arg)
        elif op.name == "GLOBAL":
            module, name = arg.split(" ", 1)
            found.append(_norm(module, name))
        elif op.name == "STACK_GLOBAL" and len(strings) >= 2:
            found.append(_norm(strings[-2], strings[-1]))
    return found


def scan_pickle_bytes(data: bytes) -> list[str]:
    """Static opcode scan. The bytes are never unpickled."""
    if data[:2] == b"PK":  # torch zip archive: scan embedded pickles
        found: list[str] = []
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                if name.endswith(".pkl"):
                    found += _scan_stream(z.read(name))
        return found
    return _scan_stream(data)


def urls_in(text: str) -> list[str]:
    return [m.group("url") for m in _MD_URL.finditer(text)]


def host_of(url: str) -> str:
    return (urlparse(url if "://" in url else "//" + url).hostname or "").lower()
