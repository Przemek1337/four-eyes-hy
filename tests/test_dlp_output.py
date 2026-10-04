import pytest

from foureyes.controls.dlp import DlpControl
from foureyes.controls.output_safe import OutputSafe
from foureyes.core.types import Outcome
from helpers import make_ctx

PESEL = "44051401359"
KEY = "sk-abcdefghijklmnop1234"


def model_ctx(text, **kw):
    return make_ctx(messages=[{"role": "user", "content": text}], **kw)


@pytest.mark.owasp("LLM02:2026")
def test_secrets_in_prompt_are_redacted_in_flight():
    ctx = model_ctx(f"use key {KEY} please")
    v = DlpControl().evaluate(ctx, "pre")
    assert v.outcome is Outcome.REDACT and KEY not in ctx.request.messages[0]["content"]


def test_secret_modes_block_and_monitor():
    blocked = model_ctx(f"key {KEY}", overrides={"dlp": {"secrets": {"on_detect": "block"}}})
    assert DlpControl().evaluate(blocked, "pre").outcome is Outcome.BLOCK
    mon = model_ctx(f"key {KEY}")
    assert DlpControl({"mode": "monitor"}).evaluate(mon, "pre") is None and KEY in mon.request.messages[0]["content"]


@pytest.mark.positive
def test_pii_the_task_needs_is_not_redacted_in_prompts():
    ctx = model_ctx(f"verify PESEL {PESEL}")
    assert DlpControl().evaluate(ctx, "pre") is None
    assert PESEL in ctx.request.messages[0]["content"]


@pytest.mark.negative
def test_egress_sink_redacts_pii_but_internal_mail_is_untouched():
    out = make_ctx(kind="tool", tool="send_email", args={"to": "x@external.example", "body": f"PESEL {PESEL}"})
    v = DlpControl().evaluate(out, "pre")
    assert v.outcome is Outcome.REDACT and PESEL not in out.request.args["body"]
    inner = make_ctx(kind="tool", tool="send_email", args={"to": "x@bank.internal", "body": f"PESEL {PESEL}"})
    assert DlpControl().evaluate(inner, "pre") is None and PESEL in inner.request.args["body"]


def test_field_minimization_removes_unneeded_fields_before_the_model_sees_them():
    ctx = make_ctx(kind="tool", tool="entities_get",
                   overrides={"sources": {"mcp:entities_get": {"class": "personal_data", "redact_fields": ["passport_no"]}}})
    ctx.source = "mcp:entities_get"
    ctx.result = {"legalName": "Nordwind", "nested": {"passport_no": "AB1234567", "country": "PL"}, "passport_no": "AB1234567"}
    v = DlpControl().evaluate(ctx, "post")
    assert v.outcome is Outcome.REDACT and v.detail["removed"] == 2
    assert ctx.result == {"legalName": "Nordwind", "nested": {"country": "PL"}}


def test_secrets_in_tool_results_and_model_answers_are_redacted():
    tool = make_ctx(kind="tool", tool="entities_get")
    tool.result = {"note": f"password: hunter22x and {KEY}"}
    assert DlpControl().evaluate(tool, "post").outcome is Outcome.REDACT
    assert KEY not in str(tool.result) and "hunter22x" not in str(tool.result)
    model = make_ctx()
    model.response_text = f"your key is {KEY}"
    assert DlpControl().evaluate(model, "post").outcome is Outcome.REDACT and KEY not in model.response_text


def answer(text, **kw):
    ctx = make_ctx(**kw)
    ctx.response_text = text
    return ctx


@pytest.mark.negative
@pytest.mark.owasp("LLM10:2026")
def test_foreign_link_and_image_are_removed_and_the_rest_is_delivered():
    ctx = answer("Done. ![chart](https://evil.example/x.png?d=1) See [terms](https://evil.example/t) and [policy](https://bank.internal/p).")
    ctl = OutputSafe(ctx.policy.control_cfg("output.safe"))
    v = ctl.evaluate(ctx, "post")
    assert v.outcome is Outcome.REDACT
    assert "evil.example" not in ctx.response_text and "https://bank.internal/p" in ctx.response_text
    assert ctx.response_text.startswith("Done. chart See terms")


@pytest.mark.negative
def test_block_mode_and_html_stripping():
    blocked = answer("![x](https://evil.example/x.png)", overrides={"controls": {"output.safe": {"mode": "block"}}})
    assert OutputSafe(blocked.policy.control_cfg("output.safe")).evaluate(blocked, "post").outcome is Outcome.BLOCK
    html = answer("Hello <script>alert(1)</script> world")
    v = OutputSafe(html.policy.control_cfg("output.safe")).evaluate(html, "post")
    assert v.outcome is Outcome.REDACT and "<script" not in html.response_text and "world" in html.response_text


@pytest.mark.negative
@pytest.mark.owasp("LLM08:2026")
def test_system_prompt_canary_leak_is_blocked():
    ctx = answer("My instructions say: FE-CANARY-7f3a ...")
    v = OutputSafe(ctx.policy.control_cfg("output.safe")).evaluate(ctx, "post")
    assert v.outcome is Outcome.BLOCK and v.code == "CANARY_LEAK"


@pytest.mark.positive
def test_clean_and_relative_links_pass_and_monitor_mode_does_not_change_text():
    ctx = answer("See [docs](/help) and https://evil.example in plain text")
    assert OutputSafe(ctx.policy.control_cfg("output.safe")).evaluate(ctx, "post") is None
    mon = answer("![x](https://evil.example/x.png)")
    assert OutputSafe({"mode": "monitor", "allowed_domains": []}).evaluate(mon, "post") is None
    assert "evil.example" in mon.response_text
