import json

import httpx
import pytest

from foureyes.upstream.base import UpstreamError
from foureyes.upstream.fake import FakeToolUpstream
from foureyes.upstream.mcp import McpUpstream
from foureyes.upstream.mock import MockModelUpstream
from foureyes.upstream.openai_compat import OpenAICompatUpstream


def test_mock_model_is_deterministic_and_can_go_down():
    up = MockModelUpstream("local", seconds=0.5, usage=(10, 5))
    r = up.chat("m", [{"role": "user", "content": "hi"}])
    assert r.message["content"] and r.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    assert r.seconds == 0.5
    up.available = False
    with pytest.raises(UpstreamError):
        up.chat("m", [])


def test_mock_model_script_controls_reply():
    up = MockModelUpstream("local", script=lambda model, messages, tools: {"role": "assistant", "content": "scripted"})
    assert up.chat("m", []).message["content"] == "scripted"


def test_openai_compat_posts_and_parses():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}],
                                         "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    up = OpenAICompatUpstream("http://x/v1", "local", client=client)
    r = up.chat("local-model", [{"role": "user", "content": "hi"}], max_tokens=7)
    assert seen["url"] == "http://x/v1/chat/completions" and seen["body"]["max_tokens"] == 7
    assert r.message["content"] == "ok" and r.usage["total_tokens"] == 5


def test_openai_compat_wraps_http_errors():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    with pytest.raises(UpstreamError):
        OpenAICompatUpstream("http://x/v1", "local", client=client).chat("m", [])


def test_mcp_upstream_round_trip():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["method"] == "tools/list":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"tools": [{"name": "t"}]}})
        args = body["params"]["arguments"]
        if args.get("fail"):
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1,
                                             "result": {"isError": True, "content": [{"type": "text", "text": "bad"}]}})
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1,
                                         "result": {"content": [{"type": "text", "text": json.dumps({"echo": args})}]}})

    up = McpUpstream("http://tools/mcp", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert up.list_tools() == [{"name": "t"}]
    assert up.call("t", {"a": 1}) == {"echo": {"a": 1}}
    with pytest.raises(UpstreamError):
        up.call("t", {"fail": True})


def test_fake_tool_upstream():
    up = FakeToolUpstream({"add": lambda a, b: {"sum": a + b}}, schemas={"add": {"type": "object"}})
    assert up.call("add", {"a": 1, "b": 2}) == {"sum": 3}
    assert up.list_tools()[0]["name"] == "add"
    with pytest.raises(UpstreamError):
        up.call("missing", {})


@pytest.mark.parametrize("reply_model,expected", [("basal-1.0-1.5B", "basal-1.0-1.5B"), (None, None), ("", None), (7, None)])
def test_openai_compat_reports_the_model_the_server_says_answered(reply_model, expected):
    body = {"choices": [{"message": {"role": "assistant", "content": "ok"}}], "usage": {}}
    if reply_model is not None:
        body["model"] = reply_model
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
    r = OpenAICompatUpstream("http://x/v1", "local", client=client).chat("basal-1.0-1.5B", [{"role": "user", "content": "hi"}])
    assert r.model == "basal-1.0-1.5B" and r.served_model == expected  # asked for a name, the server decides what answered
