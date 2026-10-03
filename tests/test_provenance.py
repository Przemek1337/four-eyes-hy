import pytest

from foureyes.controls.classify import ClassifyNetControl
from foureyes.controls.flow import FlowUntrusted
from foureyes.controls.source import SourceStage
from foureyes.core.actions import classify_action, is_outside
from foureyes.core.types import Outcome
from helpers import make_ctx

PESEL = "44051401359"


def tool_ctx(tool, args=None, labels=(), **kw):
    ctx = make_ctx(kind="tool", tool=tool, args=args or {}, **kw)
    for lab in labels:
        ctx.session.add_label(lab, "test")
    return ctx


def test_is_outside_and_classify_action():
    cfg = {"egress_arg": "to", "allowed_domains": ["bank.internal"]}
    assert not is_outside({"to": "a@bank.internal"}, cfg)
    assert not is_outside({"to": "a@sub.bank.internal"}, cfg)
    assert is_outside({"to": "a@bank.internal.evil.com"}, cfg)
    assert is_outside({}, cfg) and is_outside({"to": 5}, cfg)
    assert classify_action(tool_ctx("send_email", {"to": "x@evil.com"})) == "egress"
    assert classify_action(tool_ctx("send_email", {"to": "x@bank.internal"})) is None
    assert classify_action(tool_ctx("entities_submit")) == "critical"
    assert classify_action(tool_ctx("entities_get")) is None


@pytest.mark.positive
def test_trusted_session_is_not_restricted():
    assert FlowUntrusted().evaluate(tool_ctx("send_email", {"to": "x@evil.com"}), "pre") is None


@pytest.mark.negative
@pytest.mark.owasp("LLM01:2026")
def test_untrusted_session_egress_needs_approval():
    v = FlowUntrusted().evaluate(tool_ctx("send_email", {"to": "kyc-verify@external.example"}, labels=["untrusted"]), "pre")
    assert v.outcome is Outcome.APPROVAL and v.rule == "flow.untrusted"


@pytest.mark.positive
def test_untrusted_session_internal_email_is_allowed():
    assert FlowUntrusted().evaluate(tool_ctx("send_email", {"to": "a@bank.internal"}, labels=["untrusted"]), "pre") is None


def test_critical_depends_on_profile():
    strict = FlowUntrusted().evaluate(tool_ctx("entities_submit", labels=["untrusted"]), "pre")
    assert strict.outcome is Outcome.APPROVAL
    relaxed = tool_ctx("entities_submit", labels=["untrusted"], overrides={"profile": "relaxed"})
    assert FlowUntrusted().evaluate(relaxed, "pre").outcome is Outcome.ALLOW
    per_agent = tool_ctx("entities_submit", labels=["untrusted"],
                         overrides={"agents": {"kyc-agent": {"profile": "relaxed"}}})
    assert FlowUntrusted().evaluate(per_agent, "pre").outcome is Outcome.ALLOW


@pytest.mark.negative
def test_high_risk_requires_approval_even_in_relaxed():
    ctx = tool_ctx("entities_submit", labels=["untrusted", "high_risk"], overrides={"profile": "relaxed"})
    v = FlowUntrusted().evaluate(ctx, "pre")
    assert v.outcome is Outcome.APPROVAL and v.rule == "flow.high_risk"


def test_source_stage_applies_channel_and_tool_sources():
    pre = make_ctx(channel="document", messages=[{"role": "user", "content": "doc"}])
    SourceStage().evaluate(pre, "pre")
    assert "untrusted" in pre.session.labels and pre.session.data_class == "bank_secret"

    chat = make_ctx(channel="chat")
    SourceStage().evaluate(chat, "pre")
    assert chat.session.data_class == "public" and not chat.session.labels

    post = tool_ctx("entities_get")
    SourceStage().evaluate(post, "post")
    assert post.session.data_class == "personal_data" and post.source == "mcp:entities_get"

    reg = tool_ctx("public_registry_lookup")
    SourceStage().evaluate(reg, "post")
    assert reg.session.data_class == "public"


@pytest.mark.negative
def test_unknown_source_is_most_sensitive():
    ctx = tool_ctx("brand_new_tool")
    SourceStage().evaluate(ctx, "post")
    assert ctx.session.data_class == "bank_secret"


def prompt_ctx(text, overrides=None):
    return make_ctx(messages=[{"role": "user", "content": text}], overrides=overrides)


@pytest.mark.owasp("LLM02:2026")
def test_pesel_in_prompt_raises_class_by_default():
    ctx = prompt_ctx(f"check customer with PESEL {PESEL}")
    v = ClassifyNetControl().evaluate(ctx, "pre")
    assert ctx.session.data_class == "personal_data"
    assert v.outcome is Outcome.ALLOW and "pesel" in v.reason


@pytest.mark.positive
def test_no_detection_no_change():
    ctx = prompt_ctx("what is the weather; ticket 44051401358")  # invalid checksum
    assert ClassifyNetControl().evaluate(ctx, "pre") is None
    assert ctx.session.data_class == "public"


def test_sensitive_terms_from_session_raise_class():
    ctx = prompt_ctx("tell me about Nordwind")
    ctx.session.sensitive_terms = ["nordwind"]
    ClassifyNetControl().evaluate(ctx, "pre")
    assert ctx.session.data_class == "personal_data"


def test_on_detect_block_and_redact_modes():
    blocked = prompt_ctx(f"PESEL {PESEL}", overrides={"dlp": {"pii_in_prompt": {"on_detect": "block"}}})
    assert ClassifyNetControl().evaluate(blocked, "pre").outcome is Outcome.BLOCK
    red = prompt_ctx(f"PESEL {PESEL}", overrides={"dlp": {"pii_in_prompt": {"on_detect": "redact"}}})
    v = ClassifyNetControl().evaluate(red, "pre")
    assert v.outcome is Outcome.REDACT and PESEL not in red.request.messages[0]["content"]


def test_monitor_mode_only_alerts():
    ctx = prompt_ctx(f"PESEL {PESEL}")
    assert ClassifyNetControl({"mode": "monitor"}).evaluate(ctx, "pre") is None
    assert ctx.session.data_class == "public" and ctx.alerts
