# 2. Architecture

![FourEyes architecture](architecture.png)

FourEyes is a gateway between any agent and its upstreams. The core never imports the demo agent (`harness`), so
the same gateway serves another use case with only a policy change.

```
policy.yaml + signature feed ──(hot reload)──► PolicyStore ─► PolicySnapshot (immutable)
                                                                    │
agent / app ──► GATEWAY ──► Pipeline(Control[]) ──► Dispatcher ──► Upstream
 (any)            │            ▲ timed                 │   ├─ ModelUpstream (local | external)
                  │            │                      │   ├─ McpUpstream  (tool proxy)
                  │       SessionLabels               │   └─ HttpUpstream (other service)
                  │       (untrusted, high_risk,      ▼
                  │        data class: sticky)    RoutingModel · Meter (budgets)
                  ▼
           AuditSink (redacts) ─► audit.jsonl ─► /metrics ─► Dashboard
```

## How one request flows

Before the call (prompt or tool call), in this order:

1. `auth.agent_key`, then `models.allowlist` (model) or `authz.tools` + `authz.tool_schema` (tool)
2. `authz.scope`, `data.classify_net` (class from session labels and content; can only rise)
3. Routing: the data class decides which upstream types are allowed
4. `budget.session`, `budget.spend`, `sig.feed`
5. `sem.prompt_injection` (AI, prompts only), `flow.untrusted`, `sem.action_judge` (AI, egress and critical only)
6. `dlp.*` in flight, call upstream, decision and audit

After the call: source labels raise the session state; `sig.feed` and injection check on documents; `dlp.secrets`;
`output.safe`; real cost settled; decision and audit.

Rule that never changes: **AI controls can only tighten a deterministic decision.**

## Use case flow (KYC)

![KYC flow](kyc-flow.png)

A client uploads a document with hidden instructions. It is labelled `untrusted`. Whether or not the detector
catches it, the agent cannot approve without screening (blocked), cannot email data out without a human (approval),
and every step is logged.

## Performance metrics

| Path | What | Result | How to reproduce |
|---|---|---|---|
| Deterministic gateway overhead | 200 requests through the full pipeline, mock upstreams, no GPU | **p50 0.11 ms, p95 0.13 ms** | `make bench` |
| Slowest single control | `sig.feed` | p95 about 0.02 ms | `make bench` |
| Semantic (AI) controls, real local Basal 1.5B on RTX 4060 Laptop | prompt injection | p50 395 ms, p95 792 ms | `make eval-models` |
| | data classification | p50 112 ms, p95 115 ms | |
| | action review | p50 116 ms, p95 117 ms | |

How we keep the AI path from slowing everything down: AI controls run only where they matter (injection on
prompts and documents, action judge only on egress and critical actions); deterministic controls run first and a
`BLOCK` there never reaches the model. The Speed tab of the dashboard shows gateway overhead versus model time
live, and time per control (`/metrics`, `latency`).

The bench numbers are with mock upstreams, so they show the gateway's own cost, not model inference.
Basal numbers are from a small demo set measured on 2026-10-04.

## Data and state

| What | Where |
|---|---|
| Policy | `policy.yaml` (hot reload, validated, diffed) |
| Threat feed | `feeds/signatures.json` or a URL |
| Budgets | SQLite (`data/budgets.db`) |
| Audit | JSONL (`data/audit.jsonl`), exportable |
| Model weights | Docker volume `foureyes-basal-cache` |

More detail: [../docs/architecture.md](../docs/architecture.md) (Polish).
