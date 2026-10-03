from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    profile: Literal["strict", "relaxed"] = "strict"
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    models: dict[str, Any] = Field(default_factory=dict)
    data_classes: dict[str, Any] = Field(default_factory=lambda: {
        "order": ["public", "personal_data", "bank_secret"],
        "allowed_upstream_types": {"public": ["local", "external"],
                                   "personal_data": ["local"], "bank_secret": ["local"]},
    })
    sources: dict[str, Any] = Field(default_factory=dict)
    routing: dict[str, Any] = Field(default_factory=dict)
    agents: dict[str, dict[str, Any]] = Field(default_factory=dict)
    tools: dict[str, dict[str, Any]] = Field(default_factory=dict)
    labels: dict[str, Any] = Field(default_factory=dict)
    dlp: dict[str, Any] = Field(default_factory=dict)
    log_redaction: dict[str, Any] = Field(default_factory=dict)
    controls: dict[str, dict[str, Any]] = Field(default_factory=dict)
    signatures: dict[str, Any] = Field(default_factory=dict)
    budgets: dict[str, Any] = Field(default_factory=dict)
