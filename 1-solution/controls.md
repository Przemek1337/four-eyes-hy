# Implemented controls

All controls live in the `controls:` section of [`policy.yaml`](../policy.yaml) (the control catalog). Deleting an
entry disables the control **loudly**: the posture score drops, a `control.removed` event is logged and the dashboard
shows an alert. Code: `src/foureyes/controls/`.

Decisions are always one of: `ALLOW`, `REDACT`, `APPROVAL` (a human decides), `BLOCK`.

## Deterministic controls (no AI)

| Control | What it does | OWASP LLM |
|---|---|---|
| `auth.agent_key` | Every agent has its own key. Cannot be removed or switched off (baseline) | 03 |
| `models.allowlist` | Only listed models may be called | 03 |
| `authz.tools` | Each agent has a list of tools it may call | 03 |
| `authz.tool_schema` | Tool arguments must match a JSON schema (types, lengths, patterns, no extra fields) | 03, 05 |
| `authz.scope` | The agent sees only the client of the current case; other clients' records are refused | 09 |
| `data.classify_net` (pattern part) | Detects PESEL (with checksum), IBAN, passport, NIP written in any usual form and raises the data class | 02 |
| `route.model` | Data class decides where the call may go. Private data: local model only. A request for an external model with private data is blocked. Local model down: block, never fall back to external | 02 |
| `flow.untrusted` | The provenance wall: untrusted or `high_risk` sessions need approval for egress (email to outside the bank) and, under `strict`, for critical actions (submit a client) | 01, 05 |
| `dlp.redact_inflight` | Redacts secrets and personal fields in flight (11 kinds of secrets) | 02 |
| `log.redact` | Masks identifiers and secrets before anything is written to the audit log | 02 |
| `output.safe` | Removes foreign links and images (exfiltration through markdown), active HTML/JS, `javascript:` and `data:` URIs, and the system-prompt canary | 10, 08 |
| `budget.session` | Token and step cap per session: stops runaway loops | 06 |
| `budget.spend` | Daily and monthly limits per agent and team, in USD for external APIs and compute seconds for local models; soft limit alert at 80% | 06 |
| `sig.feed` | Known attacks from an external feed ([`feeds/signatures.json`](../feeds/signatures.json)): malicious pickle opcodes, known bad file hashes, untrusted model sources and formats, code in tool arguments, classic jailbreak phrases, invisible Unicode, exfiltration URLs. Reloaded when the file changes | 04, 01, 10 |
| Normalizer | Undoes hiding tricks before detection: look-alike letters, zero-width characters, spacing, leetspeak, full-width, base64, ROT13 | 01 |
| Tool preconditions | `requires_before` (no submit before sanctions screening) and `requires_screened_subject` (the screening must be of *this* entity); `cannot_change` (case status cannot be edited through notes) | 03, 05 |

## Semantic controls (AI, local Basal model)

| Control | Question asked | Output | Failure mode |
|---|---|---|---|
| `sem.prompt_injection` | One yes/no question per named rule (override instructions, redirect data, fake authority, jailbreak). Score = highest P(yes) | Prompt: block above 0.8, log above 0.5. Document: `high_risk` above 0.7 (no block, the wall handles it) | `fail_closed` |
| `data.classify_net` (AI part) | Which class is this text: public, personal data, bank secret? | Can only **raise** the class | uncertain answer raises the class |
| `sem.action_judge` | Is this egress or critical action within the scope of the case task? Looks only at the task and the **real** call arguments | Above 0.7 out-of-scope: approval | `approval` |

Low confidence (`min_confidence`) never invents a detection: for documents it creates a separate alert, for
classification and actions it escalates.

## Human in the loop

`APPROVAL` creates a card in the Security tab showing the real recipient and the AI judge's flag. The compliance
officer releases or denies; the decision, who made it and how long it took are logged (AI Act Art. 14 pattern).

## Invariants (in code, cannot be removed from YAML)

- `auth.agent_key` is always on.
- A private session never reaches an `external` upstream.
- The validator rejects a policy that allows `external` for a private data class, or an `external` model for a control that reads content.
