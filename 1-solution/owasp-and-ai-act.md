# OWASP Top 10 for LLM (2026) and EU AI Act

## OWASP coverage

Every control is tagged with the OWASP categories it covers (`src/foureyes/owasp.py`). The dashboard
(Management, Proof tab) shows per category: enforced / monitor only / uncovered, controls, blocks, and tests.
Remove a control from the policy and the category turns red.

| OWASP LLM (2026) | Controls |
|---|---|
| LLM01 Prompt Injection | `sem.prompt_injection`, `flow.untrusted`, `sig.feed`, `sem.action_judge`, normalizer |
| LLM02 Sensitive Information Disclosure | `data.classify_net`, `route.model`, `dlp.redact_inflight`, `log.redact` |
| LLM03 Excessive Agency | `auth.agent_key`, `models.allowlist`, `authz.tools`, `authz.tool_schema`, `sem.action_judge` |
| LLM04 Supply Chain | `sig.feed`: pickle opcodes, bad hashes, untrusted sources and formats |
| LLM05 Data and Model Poisoning | `flow.untrusted`, `authz.tool_schema`, `cannot_change` |
| LLM06 Unbounded Consumption | `budget.session`, `budget.spend` |
| LLM07 Misinformation | **gap**: no grounding control (documented) |
| LLM08 Hidden Context Exposure | `output.safe` (system-prompt canary) |
| LLM09 Vector and Embedding Weaknesses | `authz.scope` (per-client filter on shared index) |
| LLM10 Improper Output Handling | `output.safe`, `sig.feed` (exfiltration URLs) |

Tests per category: [../4-testing/README.md](../4-testing/README.md).

## EU AI Act: what we support, and what we do not claim

| AI Act theme | What FourEyes provides |
|---|---|
| Art. 12, automatic record-keeping | Every decision is written to a JSONL audit log (who, what, which control, decision, reason, cost, latency, policy version); identifiers masked; exportable (Security tab, Export audit log) |
| Art. 14, human oversight | Approval cards for egress and critical actions, with the real recipient and the AI judge's flag; the human can release or deny; decision time and expiries are tracked |
| Robustness and cybersecurity themes | Deterministic wall, fail-closed AI, signature feed, measured detection and false-block rates |
| Data governance themes | Data classes, local-only processing for private data, redaction |

**We claim alignment with these patterns, not legal compliance.** A KYC agent is not automatically a high-risk system
under the Act, and the timeline of obligations was changed by the Digital Omnibus: the dates must be verified in the
Official Journal before anyone quotes them.
