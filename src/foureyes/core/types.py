from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class Outcome(str, Enum):
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    APPROVAL = "APPROVAL"
    BLOCK = "BLOCK"


SEVERITY = {Outcome.ALLOW: 0, Outcome.REDACT: 1, Outcome.APPROVAL: 2, Outcome.BLOCK: 3}


@dataclass(frozen=True)
class Verdict:
    outcome: Outcome
    rule: str
    reason: str = ""
    layer: str = "det"  # det | ai
    owasp: tuple[str, ...] = ()
    code: str | None = None
    signature_id: str | None = None
    detail: dict = field(default_factory=dict)

    @classmethod
    def allow(cls, rule: str, reason: str = "", **kw) -> "Verdict":
        return cls(Outcome.ALLOW, rule, reason, **kw)

    @classmethod
    def redact(cls, rule: str, reason: str = "", **kw) -> "Verdict":
        return cls(Outcome.REDACT, rule, reason, **kw)

    @classmethod
    def approval(cls, rule: str, reason: str = "", **kw) -> "Verdict":
        return cls(Outcome.APPROVAL, rule, reason, **kw)

    @classmethod
    def block(cls, rule: str, reason: str = "", **kw) -> "Verdict":
        return cls(Outcome.BLOCK, rule, reason, **kw)

    def stricter_than(self, other: "Verdict") -> bool:
        return SEVERITY[self.outcome] > SEVERITY[other.outcome]


def _content_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict))
    return str(content)


def _map_content(content: Any, fn: Callable[[str], str]) -> Any:
    if isinstance(content, str):
        return fn(content)
    if isinstance(content, list):
        return [
            {**p, "text": fn(p["text"])} if isinstance(p, dict) and isinstance(p.get("text"), str) else p
            for p in content
        ]
    return content


def _map_obj(obj: Any, fn: Callable[[str], str]) -> Any:
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, dict):
        return {k: _map_obj(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_map_obj(v, fn) for v in obj]
    return obj


@dataclass
class Request:
    kind: str  # "model" | "tool"
    agent_id: str | None
    session_id: str
    channel: str = "chat"  # "chat" | "document"
    model: str | None = None
    messages: list[dict] = field(default_factory=list)
    tool: str | None = None
    args: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    @property
    def prompt_text(self) -> str:
        """User/system authored text. Tool-role messages (documents) are excluded on purpose."""
        return "\n".join(
            _content_text(m.get("content")) for m in self.messages if m.get("role") in ("user", "system")
        )

    @property
    def full_text(self) -> str:
        return "\n".join(_content_text(m.get("content")) for m in self.messages)

    @property
    def args_json(self) -> str:
        return json.dumps(self.args, sort_keys=True, ensure_ascii=False)

    def map_text(self, fn: Callable[[str], str]) -> None:
        self.messages = [{**m, "content": _map_content(m.get("content"), fn)} for m in self.messages]
        self.args = _map_obj(self.args, fn)


@dataclass
class Route:
    provider: str
    type: str  # local | external
    model: str
    allowed_types: list[str]
    router: str = "default"
    rerouted_from: str | None = None
    fallback: bool = False
