# 5. Implementation

## Code map

| Path | What |
|---|---|
| `src/foureyes/` | the gateway (Python, FastAPI): policy, pipeline, controls, routing, budgets, audit, API |
| `src/foureyes/controls/` | one file per control family (auth, scope, classify, flow, dlp, output, budget, signatures, AI controls) |
| `src/foureyes/policy/` | policy loading, validation, hot reload, the provenance wall check |
| `src/foureyes/semantic/` | decision-model clients (Basal, Granite Guardian adapter, mock) |
| `src/foureyes/api/` | `/v1/chat/completions`, `/mcp`, `/admin/*`, `/metrics`, `/audit/export` |
| `src/harness/` | the demo KYC agent, its tools and the synthetic data generators (the core never imports it) |
| `ui/` | dashboard source (React, TypeScript); built bundle in `src/foureyes/ui_dist/` |
| `tests/` | the self-testing suite, see [../4-testing](../4-testing/README.md) |
| `policy.yaml`, `feeds/signatures.json` | configuration and threat feed |
| `scripts/` | benchmark, demo traffic, Basal Dockerfile |

## Run it

| Goal | Command |
|---|---|
| Quick demo, mocked model answers | `make install && MODEL=mock make run` |
| Scripted agent, real local model | `MODEL=mock DECISION_MODELS=live make run` (Basal on `:8000`) |
| Everything in Docker (needs NVIDIA GPU) | `docker volume create foureyes-basal-cache && docker compose up -d --build --wait` |
| Rebuild the UI | `make ui` |

Dashboard at <http://127.0.0.1:8080/ui/>. Registries (KRS, Companies House) use files by default; `KRS_LIVE=1`
and `CH_API_KEY=<key>` switch to live APIs.

## How it plugs into an existing agentic ecosystem

FourEyes speaks the protocols agents already use, so no agent code has to change besides a URL and a key.

| Your agent talks to | What you do |
|---|---|
| An LLM through an OpenAI-compatible API | Point `base_url` at `http://<gateway>:8080/v1`, send `Authorization: Bearer <agent key>`. `POST /v1/chat/completions` |
| MCP tool servers | Point the MCP client at `http://<gateway>:8080/mcp` (JSON-RPC: `initialize`, `tools/list`, `tools/call`). The tool list is filtered to what the agent may use |
| Another service over HTTP | Add an upstream in the policy |

Optional headers give the gateway context: `X-FourEyes-Session`, `X-FourEyes-Task`, `X-FourEyes-Scope`
(for example `client_id=...`), `X-FourEyes-Channel`, `X-FourEyes-Approval`.

Steps to onboard a new agent:

1. Add an `agents:` entry with a key (from an environment variable), model, tools and scope.
2. Tag its tools (`critical`, `egress`) and add argument schemas.
3. Classify its data sources (`sources:`), marking outside content `untrusted`.
4. Set budgets. Save the file: the gateway reloads it. No restart and no code.

## Scalability and deployment considerations

| Topic | Today | Next step |
|---|---|---|
| Latency | Deterministic path well under 1 ms; AI controls about 100 to 800 ms and only where needed | batch or cache AI verdicts, bigger GPU |
| State | policy is an immutable snapshot per request; session labels in memory; budgets in SQLite; audit in JSONL | move sessions to Redis and audit to a log pipeline or SIEM; shared budget store |
| Horizontal scaling | single gateway process | stateless replicas behind a load balancer once sessions and budgets are shared |
| Policy distribution | file with hot reload, diff audited | policy from Git or a config service |
| Threat feed | file or URL, reloaded on change | a managed feed |
| Identity | agent keys | human identity (SSO) mapped to agents |
| Anonymization for external models | extension point only (`not_applied`) | pseudonymize before an external call |

## Honest limits

- Demo runs with mocked decision-model answers; the real local model path is tested but small (1.5B) and often abstains.
- Detection rate on our own corpus is 79.7%; the wall, not the detector, is what stops damage from the rest.
- Session state is in memory in this MVP, so a restart ends open sessions.
- No grounding control (LLM07).
