from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class YesNoDecision:
    p_yes: float
    confidence: float
    latency_ms: float
    probability_source: str = "model"  # model | logprobs | hard_label


@dataclass(frozen=True)
class ChoiceDecision:
    choice: str
    probabilities: dict[str, float]
    confidence: float
    latency_ms: float


@dataclass(frozen=True)
class AiAssessment:
    """What one AI control concluded, in the shape written to the audit log (spec §4.5)."""
    model: str
    model_version: str
    outcome: str | None  # the rule (injection), the class (data class) or the option (action judge)
    probability: float
    confidence: float
    score: float
    chunks: int
    latency_ms: float
    uncertain: bool

    def to_dict(self) -> dict:
        return {"model": self.model, "model_version": self.model_version, "rule": self.outcome,
                "probability": round(self.probability, 4), "confidence": round(self.confidence, 4),
                "score": round(self.score, 4), "chunks": self.chunks, "latency_ms": round(self.latency_ms, 2),
                "uncertain": self.uncertain}


class UncertainDecision(Exception):
    """The model answered, but below `min_confidence`. Callers map this to the stricter outcome."""

    def __init__(self, assessment: AiAssessment):
        super().__init__(f"{assessment.model} answered with confidence {assessment.confidence:.2f}")
        self.assessment = assessment


class DecisionModelClient(Protocol):
    capabilities: frozenset[str]          # subset of {"yes_no", "choice"}
    builtin_criteria: dict[str, str]      # rule name -> criterion text built into the model
    max_input_tokens: int
    model_version: str

    def yes_probability(self, state: str, criterion: str) -> YesNoDecision: ...

    def choice(self, state: str, question: str, options: dict[str, str]) -> ChoiceDecision: ...

    def healthy(self) -> bool: ...
