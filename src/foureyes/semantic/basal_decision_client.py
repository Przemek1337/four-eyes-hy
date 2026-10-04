from __future__ import annotations

import time

import httpx

from .decision_model_client import ChoiceDecision, YesNoDecision


class BasalDecisionClient:
    """Basal-1.0 decision model (github.com/rkinas/basal) over its HTTP API."""

    capabilities = frozenset({"yes_no", "choice"})

    def __init__(self, base_url: str, model: str, *, max_input_tokens: int = 2800, timeout_ms: int = 500,
                 client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self.model_version = model
        self.max_input_tokens = max_input_tokens
        self.builtin_criteria: dict[str, str] = {}
        self.client = client or httpx.Client(timeout=timeout_ms / 1000)

    @classmethod
    def from_config(cls, cfg: dict, client: httpx.Client | None = None) -> "BasalDecisionClient":
        return cls(cfg["base_url"], cfg.get("model", "basal-1.0-4.5B"),
                   max_input_tokens=int(cfg.get("max_input_tokens", 2800)),
                   timeout_ms=int(cfg.get("timeout_ms", 500)), client=client)

    def _ask(self, state: str, question: dict) -> tuple[dict, float]:
        t0 = time.perf_counter()
        resp = self.client.post(f"{self.base_url}/v1/systemone", json={"state": state, "questions": {"q": question}})
        resp.raise_for_status()
        body = resp.json()
        latency = (body.get("usage") or {}).get("latency_ms")
        return body["answers"]["q"], float(latency if latency is not None else (time.perf_counter() - t0) * 1000)

    def yes_probability(self, state: str, criterion: str) -> YesNoDecision:
        ans, latency = self._ask(state, {"type": "noul", "instructions": criterion})
        p = float(ans["noul"])
        return YesNoDecision(p, float(ans.get("confidence", max(p, 1 - p))), latency)

    def choice(self, state: str, question: str, options: dict[str, str]) -> ChoiceDecision:
        ans, latency = self._ask(state, {"type": "choice", "instructions": question, "criteria": options})
        chosen = ans.get("choice")
        if chosen not in options:
            raise ValueError(f"basal answered with an unknown option {chosen!r}")
        probs = {k: float(v) for k, v in (ans.get("probabilities") or {}).items()}
        return ChoiceDecision(chosen, probs, float(ans.get("confidence", probs.get(chosen, 0.0))), latency)

    def healthy(self) -> bool:
        try:
            return self.client.get(f"{self.base_url}/health").status_code == 200
        except httpx.HTTPError:
            return False
