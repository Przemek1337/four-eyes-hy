from __future__ import annotations

from .decision_model_client import ChoiceDecision, YesNoDecision

MOCK_JAILBREAK = "The text tries to make the assistant ignore its instructions or safeguards."


class MockDecisionClient:
    """Deterministic decision model for tests and MODEL=mock. Domain phrases come from the caller (harness/tests)."""

    capabilities = frozenset({"yes_no", "choice"})
    model_version = "mock"
    GENERIC_YES = ("ignore previous instructions", "ignore all previous", "you are now",
                   "reveal your system prompt", "ignoruj poprzednie")

    def __init__(self, yes_patterns: tuple[str, ...] = (), uncertain_patterns: tuple[str, ...] = (),
                 choice_rules: tuple[tuple[str, str], ...] = (), p_yes: float | None = None,
                 choice_result: tuple[str, float] | None = None, fail: bool = False, max_input_tokens: int = 7000):
        self.yes_patterns = self.GENERIC_YES + tuple(p.lower() for p in yes_patterns)
        self.uncertain_patterns = tuple(p.lower() for p in uncertain_patterns)
        self.choice_rules = tuple((p.lower(), o) for p, o in choice_rules)
        self.p_yes = p_yes
        self.choice_result = choice_result
        self.fail = fail
        self.max_input_tokens = max_input_tokens
        self.builtin_criteria = {"jailbreak": MOCK_JAILBREAK}
        self.calls: list[tuple[str, str]] = []

    def _check(self) -> None:
        if self.fail:
            raise RuntimeError("decision model unavailable")

    def yes_probability(self, state: str, criterion: str) -> YesNoDecision:
        self._check()
        self.calls.append(("yes_no", state))
        if self.p_yes is not None:
            p = self.p_yes
        else:
            low = state.lower()
            p = 0.95 if any(x in low for x in self.yes_patterns) else 0.6 if any(
                x in low for x in self.uncertain_patterns) else 0.03
        return YesNoDecision(p, max(p, 1 - p), 0.1)

    def choice(self, state: str, question: str, options: dict[str, str]) -> ChoiceDecision:
        self._check()
        self.calls.append(("choice", state))
        keys = list(options)
        if self.choice_result is not None:
            chosen, conf = self.choice_result
        else:
            low = state.lower()
            chosen = next((o for p, o in self.choice_rules if p in low and o in options), keys[0])
            conf = 0.95
        rest = (1 - conf) / max(len(keys) - 1, 1)
        probs = {k: (conf if k == chosen else rest) for k in keys}
        return ChoiceDecision(chosen, probs, conf, 0.1)

    def healthy(self) -> bool:
        return not self.fail
