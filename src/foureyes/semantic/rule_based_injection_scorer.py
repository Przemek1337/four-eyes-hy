from __future__ import annotations

from .decision_model_client import AiAssessment, DecisionModelClient
from .text_chunking import split_text


def assess_injection(client: DecisionModelClient, model_name: str, text: str, conf: dict) -> AiAssessment:
    """Ask every rule (yes/no) on every chunk. Score = highest P(yes); an unconfident answer lifts the score
    to at least `prompts.log_above`, so the result can only get stricter (spec §4.3)."""
    rules = conf.get("rules") or {}
    min_conf = float(conf.get("min_confidence", 0.0))
    log_above = float((conf.get("prompts") or {}).get("log_above", 0.5))
    chunks = split_text(text, client.max_input_tokens)
    best_p, best_rule, best_conf, latency, uncertain = 0.0, None, 1.0, 0.0, False
    for rule, criterion in rules.items():
        if criterion == "builtin":
            criterion = client.builtin_criteria.get(rule)
            if criterion is None:
                continue  # reported once per policy version as `rule.skipped`
        for chunk in chunks:
            d = client.yes_probability(chunk, criterion)
            latency += d.latency_ms
            uncertain |= d.confidence < min_conf
            if best_rule is None or d.p_yes > best_p:
                best_p, best_rule, best_conf = d.p_yes, rule, d.confidence
    score = max(best_p, log_above) if uncertain else best_p
    return AiAssessment(model_name, client.model_version, best_rule, best_p, best_conf, score, len(chunks), latency,
                        uncertain)
