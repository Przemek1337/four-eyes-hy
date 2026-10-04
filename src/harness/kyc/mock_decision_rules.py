"""Domain phrases for the MODEL=mock decision model. They belong to the harness, never to the core."""
from .data import HIDDEN_INSTRUCTION_PHRASES

BORDERLINE_NOTE_PREFIX = "note for automated reviewers"  # every calibrated note starts with this (Task 15)

MOCK_DECISION_RULES = {
    "yes_patterns": HIDDEN_INSTRUCTION_PHRASES,
    "uncertain_patterns": (BORDERLINE_NOTE_PREFIX,),
    "choice_rules": (
        ("przyznany limit", "bank_secret"),
        ("rating", "bank_secret"),
        ("restrukturyzac", "bank_secret"),
        ("credit committee", "bank_secret"),
        ("external.example", "out_of_scope"),
    ),
}
