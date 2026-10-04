# 3. Reporting: the dashboard

Open <http://127.0.0.1:8080/ui/> after `MODEL=mock make run`. The left menu has three tabs.
The dot at the bottom of the menu shows **Live** when the dashboard is connected to the gateway.

> Fastest way to see it full: **Playground, then "Run test attack"**. It sends a staged mix of attacks and
> legitimate requests, one at a time, and you can watch the other tabs change.

## Security tab: for the security team

*"Every agent session and what FourEyes did with it."*

| Where | What you see | What to do |
|---|---|---|
| Top: **approval queue** | Actions held for a human (for example an email to an outside address) | Open a card: it shows the real recipient and the AI judge's flag. Release or deny |
| **Session list** | One row per agent session, with filters | Click a row to open it |
| **Session detail** | Timeline of every step with decision (ALLOW, REDACT, APPROVAL, BLOCK), the control that decided, and **why blocked**; a flow map of where the data went | Use it to explain any decision |
| **Export audit log** (button) | Audit log download for analysis | Hand to the security team |

## Management tab: for managers

*"Is the control layer working, is data safe, and what does it cost?"* Seven sub-tabs:

| Sub-tab | Answers |
|---|---|
| **Overview** | Posture ring (0 to 100) with every deduction named; requests split into allowed, redacted, approval; blocked and its share; open approvals; **private data to external model** (should be 0, anything above shows a Breach alert); spend |
| **Threats** | What was blocked per hour and which controls stopped it |
| **Data** | Where each data class went (local vs external) |
| **Policy** | Control catalog and status, last policy change as a diff, summary of the active policy |
| **Cost** | Spend against agent and team budgets, in USD and compute seconds, soft-limit alerts |
| **Speed** | Gateway overhead versus model time, p50 and p95, slowest controls, throughput |
| **Proof** | Latest test results and the synthetic attack corpus: detection rate, false-block rate, **coverage per OWASP LLM category**, known gaps |

Alert bars at the top of the Management tab appear for removed controls and for private data reaching an external model.

## Playground tab: try it yourself

A chat with the agent through the gateway. Drop a PDF to send it as a client document (try the files from
`make demo-docs`). Use **Run test attack** to stage traffic. Judges can also edit `policy.yaml` and watch the
change take effect on the next request.

## Screenshots

> Add before submitting, to `3-reporting/screenshots/`.

| Screen | File |
|---|---|
| Management, Overview (posture ring, KPIs) | `screenshots/management-overview.png` (TODO) |
| Management, Threats | `screenshots/management-threats.png` (TODO) |
| Management, Cost | `screenshots/management-cost.png` (TODO) |
| Management, Proof (OWASP coverage, corpus) | `screenshots/management-proof.png` (TODO) |
| Security, session list and approval queue | `screenshots/security-sessions.png` (TODO) |
| Security, session detail (timeline, why blocked) | `screenshots/security-session-detail.png` (TODO) |
| Playground | `screenshots/playground.png` (TODO) |

## Metrics implemented

| Group | Metrics |
|---|---|
| Security posture | Posture score 0 to 100 with named deductions; controls active out of total; removed or weakened controls; signature feed status; AI model health |
| Threats | Blocked interactions and share; blocks per hour; blocks by control; blocks by OWASP category; known-attack signature hits |
| Human oversight | Open approvals; median decision time; expired approvals |
| Data protection | Requests per data class and upstream type; **private data to external model count**; redactions |
| Cost and budgets | Spend per agent and team in USD (external) and compute seconds (local); soft and hard limit status |
| Performance | Gateway p50 and p95; AI model latency; time per control; throughput per minute |
| Quality of the guardrails | Tests passed and failed, positive and negative; detection rate and false-block rate on the corpus; known gaps |
| Audit | Exportable JSONL log (`/audit/export`), identifiers masked |

Endpoints behind the dashboard: `/metrics`, `/admin/posture`, `/admin/owasp`, `/admin/controls`, `/admin/budgets`,
`/admin/signatures`, `/admin/timeseries`, `/admin/tests`, `/admin/sessions`, `/admin/approvals`.
