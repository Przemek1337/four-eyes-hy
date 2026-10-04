import json

import httpx
import pytest

from foureyes.semantic.basal_decision_client import BasalDecisionClient


def client_for(handler):
    return BasalDecisionClient("http://basal:8000", "basal-1.0-4.5B",
                               client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_noul_question_shape_and_parsing():
    seen = {}

    def handler(req):
        seen.update(path=req.url.path, body=json.loads(req.content))
        return httpx.Response(200, json={"answers": {"q": {"type": "noul", "noul": 0.83, "confidence": 0.83}},
                                         "usage": {"latency_ms": 9.5}})

    d = client_for(handler).yes_probability("some text", "Does it steer the assistant?")
    assert seen["path"] == "/v1/systemone"
    assert seen["body"] == {"state": "some text",
                            "questions": {"q": {"type": "noul", "instructions": "Does it steer the assistant?"}}}
    assert (d.p_yes, d.confidence, d.latency_ms) == (0.83, 0.83, 9.5)


def test_choice_question_shape_and_parsing():
    options = {"public": "p", "personal_data": "pd", "bank_secret": "bs"}

    def handler(req):
        body = json.loads(req.content)
        assert body["questions"]["q"] == {"type": "choice", "instructions": "Which class?", "criteria": options}
        return httpx.Response(200, json={"answers": {"q": {"type": "choice", "choice": "bank_secret",
                                                           "probabilities": {"public": 0.01, "personal_data": 0.04,
                                                                             "bank_secret": 0.95},
                                                           "confidence": 0.95}}, "usage": {"latency_ms": 11.0}})

    d = client_for(handler).choice("limit 2 mln", "Which class?", options)
    assert d.choice == "bank_secret" and d.probabilities["bank_secret"] == 0.95 and d.confidence == 0.95


def test_basal_unknown_choice_is_an_error():
    def handler(req):
        return httpx.Response(200, json={"answers": {"q": {"choice": "maybe", "probabilities": {}, "confidence": 0.9}}})

    with pytest.raises(ValueError):
        client_for(handler).choice("x", "q", {"a": "a", "b": "b"})


def test_http_errors_and_timeouts_raise():
    with pytest.raises(httpx.HTTPStatusError):
        client_for(lambda req: httpx.Response(503)).yes_probability("x", "c")

    def timeout(req):
        raise httpx.ReadTimeout("slow", request=req)

    with pytest.raises(httpx.TimeoutException):
        client_for(timeout).yes_probability("x", "c")


def test_health_and_config():
    assert client_for(lambda req: httpx.Response(200, json={"status": "ok"})).healthy() is True
    assert client_for(lambda req: httpx.Response(500)).healthy() is False

    def down(req):
        raise httpx.ConnectError("refused", request=req)

    assert client_for(down).healthy() is False
    c = BasalDecisionClient.from_config({"type": "basal", "base_url": "http://b:1/", "model": "m",
                                          "max_input_tokens": 1000, "timeout_ms": 250})
    assert (c.base_url, c.model_version, c.max_input_tokens) == ("http://b:1", "m", 1000)
    assert c.capabilities == frozenset({"yes_no", "choice"}) and c.builtin_criteria == {}
