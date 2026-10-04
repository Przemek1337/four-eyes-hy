from __future__ import annotations

import json

from .decision_model_client import AiAssessment, DecisionModelClient, UncertainDecision
from .judge import JudgeResult

DEFAULT_QUESTION = "Is this action within the scope of the case task?"


class DecisionModelActionJudge:
    """Asks a decision model whether the REAL call parameters fit the case task. Never sees document text."""

    def __init__(self, client: DecisionModelClient, model_name: str, conf: dict):
        self.client = client
        self.model_name = model_name
        self.conf = conf
        self.last_assessment: AiAssessment | None = None

    def judge(self, task: str, tool: str, args: dict, labels: list[str]) -> JudgeResult:
        state = json.dumps({"task": task, "tool": tool, "args": args, "labels": labels},
                           ensure_ascii=False, sort_keys=True)
        d = self.client.choice(state, self.conf.get("question", DEFAULT_QUESTION), self.conf["options"])
        score = float(d.probabilities.get("out_of_scope", 0.0))
        uncertain = d.confidence < float(self.conf.get("min_confidence", 0.0))
        a = AiAssessment(self.model_name, self.client.model_version, d.choice,
                         d.probabilities.get(d.choice, d.confidence), d.confidence, score, 1, d.latency_ms, uncertain)
        self.last_assessment = a
        if uncertain:
            raise UncertainDecision(a)
        return JudgeResult(d.choice == "consistent", score,
                           f"{self.model_name}: {d.choice} (P(out_of_scope)={score:.2f})")

    def healthy(self) -> bool:
        return self.client.healthy()
