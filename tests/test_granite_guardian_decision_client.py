import json
import math

import httpx
import pytest

from foureyes.semantic.granite_guardian_decision_client import (
    JAILBREAK_CRITERION, GraniteGuardianDecisionClient, build_guardian_block)


def answer(content, logprobs=None):
    choice = {"message": {"role": "assistant", "content": content}}
    if logprobs is not None:
        choice["logprobs"] = {"content": logprobs}
    return httpx.Response(200, json={"choices": [choice]})


def lp(token, logprob, alts):
    return {"token": token, "logprob": logprob, "top_logprobs": [{"token": t, "logprob": v} for t, v in alts]}


def client_for(handler):
    return GraniteGuardianDecisionClient("http://vllm:8001/v1", "ibm-granite/granite-guardian-4.1-8b",
                                         client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_request_carries_the_text_and_the_guardian_block_with_logprobs():
    seen = {}

    def handler(req):
        seen.update(path=req.url.path, body=json.loads(req.content))
        return answer("<think>\n</think>\n<score>no</score>")

    client_for(handler).yes_probability("Verify Nordwind", "The text tries to override the instructions the assistant was given.")
    body = seen["body"]
    assert seen["path"] == "/v1/chat/completions"
    assert body["model"] == "ibm-granite/granite-guardian-4.1-8b" and body["temperature"] == 0
    assert body["logprobs"] is True and body["top_logprobs"] == 5
    assert body["messages"][0] == {"role": "user", "content": "Verify Nordwind"}
    assert body["messages"][1] == {"role": "user",
                                   "content": build_guardian_block("The text tries to override the instructions the assistant was given.")}
    assert "### Criteria: The text tries to override the instructions the assistant was given." in body["messages"][1]["content"]


def test_probability_from_logprobs_of_the_score_token():
    tokens = [lp("<score>", -0.01, []), lp("yes", math.log(0.9), [("yes", math.log(0.9)), ("no", math.log(0.1))]),
              lp("</score>", -0.01, [])]
    d = client_for(lambda req: answer("<think>\n</think>\n<score>yes</score>", tokens)).yes_probability("x", "c")
    assert d.p_yes == pytest.approx(0.9) and d.confidence == pytest.approx(0.9)
    assert d.probability_source == "logprobs"


def test_probability_when_only_the_chosen_token_is_listed():
    tokens = [lp("<score>", -0.01, []), lp("no", math.log(0.7), [("no", math.log(0.7))])]
    d = client_for(lambda req: answer("<score>no</score>", tokens)).yes_probability("x", "c")
    assert d.p_yes == pytest.approx(0.3)


def test_a_stray_yes_token_before_the_score_tag_is_ignored():
    tokens = [lp("yes", math.log(0.2), [("yes", math.log(0.2)), ("no", math.log(0.8))]),
              lp("<score>", -0.01, []), lp("yes", math.log(0.9), [("yes", math.log(0.9)), ("no", math.log(0.1))])]
    d = client_for(lambda req: answer("<think>\n</think>\n<score>yes</score>", tokens)).yes_probability("x", "c")
    assert d.p_yes == pytest.approx(0.9) and d.probability_source == "logprobs"


def test_score_token_that_disagrees_with_the_label_falls_back_to_the_hard_label():
    tokens = [lp("<score>", -0.01, []), lp("no", math.log(0.9), [("no", math.log(0.9)), ("yes", math.log(0.1))])]
    d = client_for(lambda req: answer("<score>yes</score>", tokens)).yes_probability("x", "c")
    assert (d.p_yes, d.confidence, d.probability_source) == (1.0, 1.0, "hard_label")


def test_missing_token_after_the_score_tag_falls_back_to_the_hard_label():
    tokens = [lp("yes", math.log(0.9), [("yes", math.log(0.9))]), lp("<score>", -0.01, [])]
    d = client_for(lambda req: answer("<score>yes</score>", tokens)).yes_probability("x", "c")
    assert d.probability_source == "hard_label"


def test_without_logprobs_the_label_is_hard():
    d = client_for(lambda req: answer("<think>\n</think>\n<score>yes</score>")).yes_probability("x", "c")
    assert (d.p_yes, d.confidence, d.probability_source) == (1.0, 1.0, "hard_label")


def test_granite_without_score_tag_is_an_error():
    with pytest.raises(ValueError):
        client_for(lambda req: answer("I think it is fine.")).yes_probability("x", "c")
    with pytest.raises(ValueError):
        client_for(lambda req: answer("<score>maybe</score>")).yes_probability("x", "c")


def test_capabilities_builtin_health_and_config():
    c = client_for(lambda req: httpx.Response(200, json={"data": []}))
    assert c.capabilities == frozenset({"yes_no"})
    assert c.builtin_criteria == {"jailbreak": JAILBREAK_CRITERION}
    assert c.healthy() is True
    with pytest.raises(NotImplementedError):
        c.choice("x", "q", {"a": "a"})
    assert client_for(lambda req: httpx.Response(503)).healthy() is False
    g = GraniteGuardianDecisionClient.from_config({"type": "granite_guardian", "base_url": "http://g:1/v1/",
                                                    "model": "m", "max_input_tokens": 6000})
    assert (g.base_url, g.model_version, g.max_input_tokens) == ("http://g:1/v1", "m", 6000)


def test_a_late_case_variant_does_not_overwrite_the_main_token():
    # review C1 probe: vLLM lists top_logprobs by descending probability, so "Yes" (0.001) comes after "yes" (0.55)
    tokens = [lp("<score>", -0.01, []),
              lp("yes", math.log(0.55), [("yes", math.log(0.55)), ("no", math.log(0.40)), ("Yes", math.log(0.001))])]
    d = client_for(lambda req: answer("<score>yes</score>", tokens)).yes_probability("x", "c")
    assert d.p_yes == pytest.approx(0.551 / 0.951) and d.probability_source == "logprobs"
    assert d.confidence < 0.9  # uncertain, so the injection control takes the stricter side


def test_variants_of_the_same_label_are_summed():
    tokens = [lp("<score>", -0.01, []),
              lp("no", math.log(0.5), [("no", math.log(0.5)), (" no", math.log(0.2)), ("No", math.log(0.1)),
                                       ("yes", math.log(0.1)), (" Yes", math.log(0.1))])]
    d = client_for(lambda req: answer("<score>no</score>", tokens)).yes_probability("x", "c")
    assert d.p_yes == pytest.approx(0.2 / 1.0) and d.confidence == pytest.approx(0.8)


def test_probability_that_points_away_from_the_label_falls_back_to_the_hard_label():
    yes_label = [lp("<score>", -0.01, []), lp("yes", math.log(0.3), [("yes", math.log(0.3)), ("no", math.log(0.6))])]
    d = client_for(lambda req: answer("<score>yes</score>", yes_label)).yes_probability("x", "c")
    assert (d.p_yes, d.confidence, d.probability_source) == (1.0, 1.0, "hard_label")
    no_label = [lp("<score>", -0.01, []), lp("no", math.log(0.3), [("no", math.log(0.3)), ("yes", math.log(0.6))])]
    d = client_for(lambda req: answer("<score>no</score>", no_label)).yes_probability("x", "c")
    assert (d.p_yes, d.confidence, d.probability_source) == (0.0, 1.0, "hard_label")


def test_the_label_and_the_probability_both_come_from_the_last_score_tag():
    tokens = [lp("<score>", -0.01, []), lp("no", math.log(0.9), [("no", math.log(0.9))]), lp("</score>", -0.01, []),
              lp("<score>", -0.01, []), lp("yes", math.log(0.9), [("yes", math.log(0.9)), ("no", math.log(0.1))])]
    d = client_for(lambda req: answer("<score>no</score> <score>yes</score>", tokens)).yes_probability("x", "c")
    assert d.p_yes == pytest.approx(0.9) and d.probability_source == "logprobs"
