from __future__ import annotations

from foureyes.semantic.decision_model_client import AiAssessment, DecisionModelClient
from foureyes.semantic.text_chunking import split_text

DEFAULT_QUESTION = "Which class of data does this text contain?"


def classify_data(client: DecisionModelClient, model_name: str, text: str, conf: dict,
                  class_order: list[str]) -> AiAssessment:
    """Highest class over all chunks; an unconfident chunk counts as the highest class (spec §4.3)."""
    classes = conf["classes"]
    min_conf = float(conf.get("min_confidence", 0.0))
    chunks = split_text(text, client.max_input_tokens)
    best, best_d, latency, uncertain = class_order[0], None, 0.0, False
    for chunk in chunks:
        d = client.choice(chunk, conf.get("question", DEFAULT_QUESTION), classes)
        latency += d.latency_ms
        cls = d.choice
        if d.confidence < min_conf:
            cls, uncertain = class_order[-1], True
        if best_d is None or class_order.index(cls) > class_order.index(best):
            best, best_d = cls, d
    probability = best_d.probabilities.get(best_d.choice, best_d.confidence)
    return AiAssessment(model_name, client.model_version, best, probability, best_d.confidence, probability,
                        len(chunks), latency, uncertain)
