# Configuration: one policy file

Everything is in [`policy.yaml`](../policy.yaml): controls, thresholds, allowed models, budgets, who may call what.
The file is commented line by line. The gateway **reloads it on the next request**; a file with a mistake is rejected
(event `policy.rejected`) and the previous version stays active. Every change is audited with a diff.

## Sections

| Section | What you configure |
|---|---|
| `profile` | Strictness: `strict` (untrusted session needs a human for critical actions) or `relaxed` (only egress and `high_risk`). Per agent override: `agents.<id>.profile` |
| `providers`, `models.allowlist` | Where model calls may go, and which models are allowed. Costs per 1k tokens (external) or per compute second (local) so the dashboard shows one currency |
| `data_classes`, `sources` | `public < personal_data < bank_secret`; which upstream types each class may use; the class and labels (`untrusted`) of every data source. Unknown source = most sensitive (fail closed) |
| `agents` | One key, default model, team, tool list and scope per agent |
| `tools` | Tags (`critical`, `egress`), argument schemas, `requires_before`, `allowed_domains`, `cannot_change` |
| `labels.rules` | The provenance wall: what an `untrusted` or `high_risk` session may do |
| `dlp`, `log_redaction` | `redact`, `block`, `monitor` or `raise_class` per data type |
| `controls` | The control catalog with `mode` and thresholds |
| `decision_models` | Local decision models and their limits |
| `signatures` | Path or URL of the external threat feed |
| `budgets` | Session caps, agent and team budgets, `soft_limit_pct`, `on_exceeded: block / fallback_local / approval` |

## Strictness levels (examples)

| Setting | Strict (default) | Relaxed |
|---|---|---|
| `profile` | untrusted session: egress **and** critical need approval | only egress and `high_risk` sessions |
| `prompts.block_above` | 0.8 | 0.95: fewer blocks, more risk accepted |
| control `mode` | `enforce` | `monitor`: logs only, counts as half in the posture score |
| `budgets.on_exceeded` | `block` | `fallback_local` or `approval` |

## Try it live (each takes effect on the next request)

1. `profile: relaxed`: untrusted sessions no longer need a human for critical actions.
2. `prompts.block_above: 0.8` to `0.95`: prompts scored between 0.8 and 0.95 are no longer blocked.
3. Delete the `dlp.redact_inflight` line: the control stops, posture drops, the dashboard raises an alert.
4. Lower `budgets.agents.kyc-agent.daily_usd`: the budget bites from the next request.
5. Add a signature to [`feeds/signatures.json`](../feeds/signatures.json): it is active as soon as the file is saved.

## Adding a new use case

Add an agent, its tools with tags, its sources with classes, limits and a profile to `policy.yaml`. No code change.
`tests/test_generality.py` proves it with a payments agent defined only in YAML.
