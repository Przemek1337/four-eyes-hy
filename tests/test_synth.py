"""The synthetic generators are the foundation of the corpus tests, so they are tested first:
identifiers must pass the same checksums the detectors use, and everything must be reproducible from a seed."""
import random

import pytest

from foureyes.detect.normalize import variants
from foureyes.detect.patterns import find_all
from harness.kyc import synth

SEEDS = range(40)


@pytest.mark.parametrize("seed", SEEDS)
def test_generated_identifiers_pass_their_checksums(seed):
    rng = random.Random(seed)
    assert find_all(synth.pesel(rng), ["pesel"])
    assert find_all(synth.iban_pl(rng), ["iban"]) and find_all(synth.iban_pl(rng, spaced=False), ["iban"])
    assert find_all(synth.passport_pl(rng), ["passport"])
    nip = synth.nip(rng)
    weights = (6, 5, 7, 2, 3, 4, 5, 6, 7)
    assert len(nip) == 10 and sum(int(d) * w for d, w in zip(nip, weights)) % 11 == int(nip[9])


@pytest.mark.parametrize("seed", SEEDS)
def test_look_alike_numbers_are_not_pesel(seed):
    assert not find_all(synth.not_a_pesel(random.Random(seed)), ["pesel"])


@pytest.mark.parametrize("kind", ["openai", "aws", "github", "password", "bearer"])
def test_generated_secrets_are_detected(kind):
    for seed in range(10):
        assert find_all(synth.secret(random.Random(seed), kind), ["secrets"])


def test_generation_is_deterministic_and_varied():
    a = [synth.company(random.Random(7), i) for i in range(3)]
    b = [synth.company(random.Random(7), i) for i in range(3)]
    assert a == b
    rng = random.Random(1)
    assert len({synth.pesel(rng) for _ in range(50)}) > 40
    assert len({synth.company(rng)["legalName"] for _ in range(50)}) > 8


def test_documents_embed_what_they_claim_to():
    rng = random.Random(3)
    co = synth.company(rng)
    doc = synth.clean_document(rng, co, with_pii=True)
    assert co["legalName"] in doc and co["director"]["pesel"] in doc and co["director"]["iban"] in doc
    poisoned = synth.poisoned_document(rng, synth.INSTRUCTIONS_EN[4], "white_text")
    assert "Skip sanctions" in poisoned and "[hidden, white text]" in poisoned


@pytest.mark.parametrize("technique", sorted(synth.TECHNIQUES))
def test_every_technique_changes_the_text_but_keeps_it_recoverable(technique):
    original = synth.INSTRUCTIONS_EN[0]
    disguised = synth.TECHNIQUES[technique](original)
    if technique != "plain":
        assert disguised != original
    if technique not in {"leet", "roleplay", "translate_frame", "json_field", "html_comment", "markdown_comment",
                         "white_text", "spaced"}:
        # for the pure encodings, one of the normalised readings must contain the sentence again
        assert any("ignore previous instructions" in v.lower() for v in variants(disguised)), technique


def test_normalisation_leaves_ordinary_text_alone():
    text = "Share capital is 50,000 PLN; the order number 1234567890 was shipped."
    assert variants(text)[0] == text and all("ignore" not in v.lower() for v in variants(text))
