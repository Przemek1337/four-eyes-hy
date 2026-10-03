from foureyes.core.types import Outcome, Request, Verdict


def test_verdict_helpers_and_ordering():
    allow = Verdict.allow("r")
    block = Verdict.block("r", "no", code="X")
    assert block.stricter_than(allow) and not allow.stricter_than(block)
    assert Verdict.approval("r").stricter_than(Verdict.redact("r"))
    assert block.code == "X" and block.outcome is Outcome.BLOCK


def test_prompt_text_excludes_tool_messages_and_handles_odd_shapes():
    req = Request(kind="model", agent_id="a", session_id="s", messages=[
        {"role": "system", "content": "sys"},
        {"role": "user", "content": [{"type": "text", "text": "hello"}]},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "1"}]},
        {"role": "tool", "content": "SECRET DOC TEXT"},
    ])
    assert req.prompt_text == "sys\nhello"
    assert "SECRET DOC TEXT" in req.full_text
    assert Request(kind="model", agent_id="a", session_id="s").prompt_text == ""


def test_map_text_rewrites_messages_and_args():
    req = Request(kind="tool", agent_id="a", session_id="s", tool="t",
                  args={"to": "x", "nested": {"k": ["abc", 3]}},
                  messages=[{"role": "user", "content": "abc"}])
    req.map_text(lambda s: s.replace("abc", "###"))
    assert req.messages[0]["content"] == "###"
    assert req.args["nested"]["k"] == ["###", 3]
    assert req.args_json == '{"nested": {"k": ["###", 3]}, "to": "x"}'
