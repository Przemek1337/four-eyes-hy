import pytest

from foureyes.controls.allowlist import ModelsAllowlist
from foureyes.controls.auth import AgentKeyControl
from foureyes.controls.scope import ScopeControl
from foureyes.controls.tool_schema import ToolSchemaControl
from foureyes.controls.tools import AuthzTools
from foureyes.core.types import Outcome
from helpers import make_ctx


def tool_ctx(tool, args=None, **kw):
    return make_ctx(kind="tool", tool=tool, args=args or {}, **kw)


@pytest.mark.negative
@pytest.mark.owasp("LLM03:2026")
def test_missing_agent_key_is_blocked():
    ctx = make_ctx(agent=None)
    ctx.request.agent_id = None
    v = AgentKeyControl().evaluate(ctx, "pre")
    assert v.outcome is Outcome.BLOCK and v.code == "AUTH_FAILED"


@pytest.mark.positive
def test_known_agent_passes():
    assert AgentKeyControl().evaluate(make_ctx(), "pre") is None


def test_model_allowlist():
    assert ModelsAllowlist().evaluate(make_ctx(model="basal-1.0-1.5B"), "pre") is None
    assert ModelsAllowlist().evaluate(make_ctx(model="auto"), "pre") is None
    v = ModelsAllowlist().evaluate(make_ctx(model="gpt-unknown"), "pre")
    assert v.code == "MODEL_NOT_ALLOWED"


@pytest.mark.negative
@pytest.mark.owasp("LLM03:2026")
def test_tool_not_in_agent_list_is_blocked():
    v = AuthzTools().evaluate(tool_ctx("payments_execute"), "pre")
    assert v.code == "TOOL_NOT_ALLOWED"


@pytest.mark.negative
@pytest.mark.owasp("LLM03:2026")
def test_tool_order_requires_sanctions_check_before_submit():
    ctx = tool_ctx("entities_submit")
    assert AuthzTools().evaluate(ctx, "pre").code == "TOOL_ORDER"
    ctx.session.note_tool("sanctions_check")
    assert AuthzTools().evaluate(ctx, "pre").code == "SCREENING_SUBJECT_MISMATCH"  # screened nobody this call acts on
    ctx.session.task = "KYC for Nordwind Sp. z o.o."
    ctx.session.note_screened("nordwindspzoo")
    assert AuthzTools().evaluate(ctx, "pre") is None


GOOD = {"legalName": "Nordwind Sp. z o.o.", "legalStructure": "sp_zoo", "country": "PL"}


@pytest.mark.positive
def test_valid_entity_create_passes_schema():
    assert ToolSchemaControl().evaluate(tool_ctx("entities_create", GOOD), "pre") is None


@pytest.mark.negative
@pytest.mark.parametrize("bad", [
    {k: v for k, v in GOOD.items() if k != "legalName"},
    {**GOOD, "legalStructure": "llc_cayman"},
    {**GOOD, "country": "XX"},
    {**GOOD, "extra": "field"},
])
def test_schema_violations_are_blocked(bad):
    v = ToolSchemaControl().evaluate(tool_ctx("entities_create", bad), "pre")
    assert v.outcome is Outcome.BLOCK and v.rule == "authz.tool_schema"


PAYMENTS = {"tools": {"payments_execute": {
    "tags": ["critical"],
    "schema": {"type": "object", "required": ["amount", "beneficiary"],
               "properties": {"amount": {"type": "number", "maximum": 10000},
                              "beneficiary": {"enum": ["ACME-1", "ACME-2"]}}},
    "on_violation": {"amount": "approval", "beneficiary": "block"}}}}


def test_per_rule_on_violation_approval_vs_block():
    ok = ToolSchemaControl().evaluate(tool_ctx("payments_execute", {"amount": 8000, "beneficiary": "ACME-1"}, overrides=PAYMENTS), "pre")
    assert ok is None
    big = ToolSchemaControl().evaluate(tool_ctx("payments_execute", {"amount": 2_000_000, "beneficiary": "ACME-1"}, overrides=PAYMENTS), "pre")
    assert big.outcome is Outcome.APPROVAL
    unknown = ToolSchemaControl().evaluate(tool_ctx("payments_execute", {"amount": 5, "beneficiary": "EVIL"}, overrides=PAYMENTS), "pre")
    assert unknown.outcome is Outcome.BLOCK
    both = ToolSchemaControl().evaluate(tool_ctx("payments_execute", {"amount": 2_000_000, "beneficiary": "EVIL"}, overrides=PAYMENTS), "pre")
    assert both.outcome is Outcome.BLOCK


@pytest.mark.negative
@pytest.mark.owasp("LLM05:2026")
def test_immutable_fields_cannot_be_changed_through_tools():
    v = ToolSchemaControl().evaluate(tool_ctx("update_case_notes", {"note": "pre-approved", "case_status": "APPROVED"}), "pre")
    assert v.code == "FIELD_IMMUTABLE"
    assert ToolSchemaControl().evaluate(tool_ctx("update_case_notes", {"note": "hello"}), "pre") is None


def scoped(tool, args, scope=None):
    ctx = tool_ctx(tool, args)
    ctx.session.scope = {"client_id": "C1"} if scope is None else scope
    return ctx


@pytest.mark.negative
@pytest.mark.owasp("LLM09:2026")
def test_search_without_scope_filter_is_blocked():
    assert ScopeControl().evaluate(scoped("search_documents", {"query": "x"}), "pre").code == "SCOPE_FILTER_MISSING"
    assert ScopeControl().evaluate(scoped("search_documents", {"query": "x", "client_id": "C2"}), "pre").code == "SCOPE_VIOLATION"
    assert ScopeControl().evaluate(scoped("search_documents", {"query": "x"}, scope={}), "pre").code == "SCOPE_UNKNOWN"


@pytest.mark.positive
def test_search_with_own_scope_passes():
    assert ScopeControl().evaluate(scoped("search_documents", {"query": "x", "client_id": "C1"}), "pre") is None


@pytest.mark.negative
@pytest.mark.owasp("LLM09:2026")
def test_results_from_other_clients_are_filtered_out():
    ctx = scoped("search_documents", {"query": "x", "client_id": "C1"})
    ctx.result = {"results": [{"client_id": "C1", "text": "a"}, {"client_id": "C2", "text": "b"}, {"text": "no key"}]}
    v = ScopeControl().evaluate(ctx, "post")
    assert v.outcome is Outcome.REDACT and v.detail["removed"] == 2
    assert ctx.result["results"] == [{"client_id": "C1", "text": "a"}]


EGRESS = {"allowed_domains": ["bank.internal"], "egress_arg": "to"}


@pytest.mark.negative
@pytest.mark.owasp("LLM01:2026")
@pytest.mark.parametrize("to", [
    "evil@x.com, ok@bank.internal", "evil@x.com;ok@bank.internal", "ok@bank.internal, evil@x.com",
    "evil@x.com@bank.internal", "ok@bank.internal evil@x.com", "Evil <evil@x.com>, Boss <ok@bank.internal>",
    "ok@bank.internal.evil.com", ["ok@bank.internal", "evil@x.com"], "", None])
def test_every_recipient_must_be_inside_the_bank(to):
    from foureyes.core.actions import is_outside
    assert is_outside({"to": to}, EGRESS)


@pytest.mark.negative
@pytest.mark.parametrize("extra", ["cc", "bcc", "reply_to"])
def test_hidden_recipient_fields_are_checked(extra):
    from foureyes.core.actions import is_outside
    assert is_outside({"to": "ok@bank.internal", extra: "evil@x.com"}, EGRESS)


@pytest.mark.positive
@pytest.mark.parametrize("to", ["ok@bank.internal", "a@bank.internal, b@bank.internal", "Boss <ok@mail.bank.internal>",
                                ["a@bank.internal", "b@bank.internal"]])
def test_internal_recipients_stay_inside(to):
    from foureyes.core.actions import is_outside
    assert not is_outside({"to": to, "cc": "c@bank.internal"}, EGRESS)


@pytest.mark.positive
def test_screening_tolerates_a_dropped_legal_form_but_not_another_company():
    from foureyes.controls.tools import fold, same_subject
    assert same_subject(fold("Nordwind"), fold("Nordwind Sp. z o.o."))
    assert not same_subject(fold("Acme Holdings"), fold("Nordwind Sp. z o.o."))
    assert not same_subject(fold("AB"), fold("ABC Ltd"))  # too short to count as a match
