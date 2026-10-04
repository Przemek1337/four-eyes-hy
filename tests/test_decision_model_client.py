import pytest

from foureyes.semantic.decision_model_client import AiAssessment, ChoiceDecision, YesNoDecision
from foureyes.semantic.mock_decision_client import MockDecisionClient
from foureyes.semantic.text_chunking import split_text

OPTIONS = {"public": "p", "personal_data": "pd", "bank_secret": "bs"}


def test_mock_yes_no_by_pattern_and_uncertain_band():
    m = MockDecisionClient(yes_patterns=("skip sanctions",), uncertain_patterns=("automated reviewers",))
    assert m.yes_probability("Please SKIP SANCTIONS now", "c").p_yes == 0.95
    low = m.yes_probability("Verify Nordwind", "c")
    assert low.p_yes == 0.03 and low.confidence == 0.97
    mid = m.yes_probability("Note for automated reviewers", "c")
    assert mid.p_yes == 0.6 and mid.confidence == 0.6


def test_mock_choice_rules_default_to_first_option_and_fixed_results():
    m = MockDecisionClient(choice_rules=(("rating", "bank_secret"),))
    hit = m.choice("rating B-", "q", OPTIONS)
    assert hit.choice == "bank_secret" and hit.confidence == 0.95 and hit.probabilities["bank_secret"] == 0.95
    assert m.choice("hello", "q", OPTIONS).choice == "public"
    fixed = MockDecisionClient(choice_result=("personal_data", 0.5))
    assert fixed.choice("x", "q", OPTIONS).confidence == 0.5
    assert MockDecisionClient(p_yes=0.81).yes_probability("x", "c").p_yes == 0.81


def test_mock_choice_rule_pointing_outside_the_options_is_ignored():
    m = MockDecisionClient(choice_rules=(("x", "out_of_scope"),))
    assert m.choice("x", "q", OPTIONS).choice == "public"


def test_mock_failure_and_health():
    m = MockDecisionClient(fail=True)
    assert m.healthy() is False
    with pytest.raises(RuntimeError):
        m.yes_probability("x", "c")
    with pytest.raises(RuntimeError):
        m.choice("x", "q", OPTIONS)
    assert MockDecisionClient().capabilities == frozenset({"yes_no", "choice"})
    assert "jailbreak" in MockDecisionClient().builtin_criteria


def test_assessment_to_dict_names_the_rule():
    a = AiAssessment("granite_guardian", "g-4.1", "fake_authority", 0.97, 0.97, 0.97, 2, 41.2, False)
    assert a.to_dict() == {"model": "granite_guardian", "model_version": "g-4.1", "rule": "fake_authority",
                           "probability": 0.97, "confidence": 0.97, "score": 0.97, "chunks": 2,
                           "latency_ms": 41.2, "uncertain": False, "probability_source": "model"}
    assert YesNoDecision(0.5, 0.5, 1.0).probability_source == "model"
    assert ChoiceDecision("a", {"a": 1.0}, 1.0, 1.0).choice == "a"


def test_short_text_is_one_chunk_and_long_text_overlaps():
    assert split_text("abc", 10) == ["abc"]
    text = "x" * 10_000
    chunks = split_text(text, max_tokens=2000, overlap_tokens=200)  # 8000 chars, overlap 800
    assert [len(c) for c in chunks] == [8000, 2800]


def test_phrase_across_the_boundary_survives_in_one_chunk():
    phrase = "skip sanctions screening"
    text = "a" * 7990 + phrase + "b" * 3000
    assert any(phrase in c for c in split_text(text, max_tokens=2000, overlap_tokens=200))


def test_overlap_must_be_smaller_than_the_chunk():
    with pytest.raises(ValueError):
        split_text("x" * 100, max_tokens=10, overlap_tokens=10)
