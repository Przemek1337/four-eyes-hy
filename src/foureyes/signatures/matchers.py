from __future__ import annotations

import io
import pickletools
import re
import zipfile
from urllib.parse import urlparse

_ZERO_WIDTH = {chr(c) for c in (0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x2060, 0xFEFF)}
_MD_URL = re.compile(r"!?\[[^\]]*\]\((?P<url>[^)\s]+)[^)]*\)")
_OTHER_URLS = re.compile(
    r"""(?:^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*<?(?P<ref>\S+?)>?(?:[ \t]|$))"""      # [1]: https://host
    r"""|(?:<(?P<auto>(?:https?:)?//[^\s<>]+)>)"""                                    # <https://host>
    r"""|(?:\b(?:src|href|srcset|action|poster|data)\s*=\s*["']?(?P<attr>(?:https?:)?//[^\s"'>]+))"""  # html attrs
    r"""|(?:(?<![\w(<"'=/])(?P<bare>https?://[^\s<>")\]]+))""", re.I | re.M)         # bare URL


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
    """Every URL in a model answer: inline markdown, reference definitions, autolinks, HTML attributes, bare links."""
    found = [m.group("url") for m in _MD_URL.finditer(text)]
    found += [next(g for g in m.groups() if g) for m in _OTHER_URLS.finditer(text)]
    return found


def host_of(url: str) -> str:
    url = url.strip()
    return (urlparse(url if "://" in url or url.startswith("//") else "//" + url).hostname or "").lower()


def looks_like_pickle(data: bytes) -> bool:
    """A pickle stream starts with the PROTO opcode; a torch archive is a zip holding one."""
    return (len(data) > 2 and data[0] == 0x80 and 2 <= data[1] <= 5) or data[:2] == b"PK"


def content_matches_format(ext: str, data: bytes) -> bool:
    """Magic-byte check for the formats the policy allows, so a pickle cannot pass under a safe-looking name."""
    if ext == "gguf":
        return data[:4] == b"GGUF"
    if ext == "safetensors":
        # 8-byte little-endian header length, then a JSON header
        return len(data) > 9 and data[8:9] == b"{" and int.from_bytes(data[:8], "little") < len(data)
    return True
