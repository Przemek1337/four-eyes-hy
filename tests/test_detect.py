import pytest

from foureyes.detect.patterns import drop_keys, find_all, redact_obj, redact_text

PESEL = "44051401359"
IBAN = "PL61 1090 1014 0000 0712 1981 2874"


def test_pesel_requires_valid_checksum():
    assert find_all(f"pesel {PESEL}", ["pesel"])
    assert not find_all("pesel 44051401358", ["pesel"])
    assert not find_all("order 123456789012345", ["pesel"])


@pytest.mark.parametrize("text", [f"iban {IBAN} end", "iban PL61109010140000071219812874.", "DE89 3704 0044 0532 0130 00"])
def test_iban_with_and_without_spaces(text):
    assert find_all(text, ["iban"])


def test_iban_rejects_bad_checksum():
    assert not find_all("PL61 1090 1014 0000 0712 1981 2875", ["iban"])


def test_passport_and_secrets():
    assert find_all("passport AB1234567.", ["passport"])
    assert find_all("sk-abcdefghijklmnop1234", ["secrets"])
    assert find_all("password: hunter22x", ["secrets"])
    assert not find_all("a normal sentence about passwords", ["secrets"])


def test_redact_text_merges_overlaps_and_counts():
    out, n = redact_text(f"pesel {PESEL} iban {IBAN}", ["pesel", "iban"])
    assert out == "pesel [REDACTED] iban [REDACTED]" and n == 2


def test_redact_obj_and_drop_keys_are_deep():
    obj = {"a": [f"x {PESEL}", {"b": "ok"}], "n": 3}
    new, n = redact_obj(obj, ["pesel"])
    assert new["a"][0] == "x [REDACTED]" and new["n"] == 3 and n == 1
    cleaned, dropped = drop_keys({"p": 1, "q": {"p": 2, "keep": 3}}, ["p"])
    assert cleaned == {"q": {"keep": 3}} and dropped == 2
