# FourEyes Dashboard: UI Design Spec

Status: approved 2026-10-04. Reference implementation of the look: `docs/design/key-visual/index.html` (static, open it in a browser; routes `#list`, `#session`, `#management`, `#chat`, `#states`). Where this spec and `docs/superpowers/plans/2026-10-03-foureyes-ui.md` disagree on visuals, **this spec wins**. Behaviour, component props and tests in the plan stay as written.

## 1. Direction

Black canvas, white and grey type, **one** accent: acid lime. No other hue anywhere. The accent is not decoration. It means "FourEyes holds the line or a human is needed": a blocked action, an action waiting for compliance, the posture ring, the `private → external 0` invariant, the live dot.

Every state is also readable without colour (shape, fill, symbol, line style), so the UI survives colour blindness, projectors and greyscale printing.

## 2. Tokens

```css
:root{
  --ink:#0A0A0A;      /* page */
  --surface:#141414;  /* cards, approval card, inputs */
  --line:#262626;     /* hairlines */
  --text:#F5F5F2;
  --muted:#A3A39E;    /* secondary text, 5.3:1 on surface */
  --faint:#7E7E79;    /* tertiary text and dashed borders, 4.5:1 minimum */
  --hold:#C8F560;     /* the only accent */
  --sans:"Inter",ui-sans-serif,system-ui,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,Menlo,monospace;
}
```

- **Dark only.** No light theme (not required, halves the QA surface).
- **Fonts:** Inter 400/500/600/700 for everything; JetBrains Mono 400 only for evidence, ids, hashes, parameters and code. Bundle both with `@fontsource/inter` and `@fontsource/jetbrains-mono` through Vite. No CDN: the demo runs offline. (The key visual loads Google Fonts for preview only.)
- **Type scale:** page title `clamp(28px,3.2vw,40px)` 600, `-0.025em`; section title 20/600; body 15/1.6; secondary 13–14; numbers use `font-variant-numeric: tabular-nums`; large numbers 36–56 at 600–700. No all-caps labels.
- **Radii by hierarchy:** approval card 28, queue and alert bars 20–24, tiles and cards 16–18, inputs 12, pills and buttons 999.
- **Layout:** left sidebar 272 px (logo of four dots, nav Security / Management / Chat, `Private → external` and live dot at the bottom); content max 1280 px, 48 px page padding; 72 px between sections; 44 px between timeline steps. Below 1180 px the approval card moves under the timeline; below 820 px the sidebar becomes a top bar. Must work at 360 px with no horizontal page scroll.
- **Text safety:** `overflow-wrap:anywhere` on `body`; all event and approval text rendered as text only.

## 3. State language (replaces colour semantics in the plan)

| Meaning | Rendering |
|---|---|
| `Allow` | grey outline pill |
| `Redact` | dashed grey outline pill |
| `Approval` (waiting for a human) | **lime outline**, lime text |
| `Block` (stopped by the system) | **lime filled pill with ✕**; on the timeline a larger lime node with ✕ and a lime-tinted card |
| `untrusted` | dashed ring, dashed timeline line, and a lightly tinted band from the first untrusted step to the end with the note "Session is untrusted from here" |
| `high_risk` | filled white dot |
| `clean` | hollow grey ring |
| Posture score | lime ring, number in the centre, explicit deduction line below |
| OWASP coverage | filled dot = enforced, half dot = monitor only, dashed hollow = uncovered |
| Budget bar | white fill; at or above the soft limit (80%) lime fill |
| `private → external` | `0` in lime; above 0 the breach block (lime outline, `Breach` pill) |
| Control `REMOVED` | struck-through id, lime filled `Removed` pill, alert bar on Management, diff under the table |
| Live connection | pulsing lime dot = live; hollow ring = polling; `✕` = offline |

Primary vs secondary actions: on an approval the safe action is primary (**Deny**, white solid, wider); **Approve** is secondary (outline). Lime never fills a button that approves something risky.

Motion: timeline line draws once on load, live dot pings, waiting dots blink, posture ring animates when it changes. Everything else is static. `prefers-reduced-motion` turns all of it off.

## 4. Views

**Security** (`#list`): title and one-line sub; queue bar (lime outline) with the pending approval and a Review button; filters (All, Blocked, Needs approval, agent, data class, rule); Export audit log button opens a dialog; sessions table (session, agent, client, status, last decision, steps, started), rows clickable.

**Session detail** (`#session`): back link; plain-language title that says what the agent *tried* and that the system stopped it; meta line (agent, user, team, id, start, steps); label chips; **Where the data went** (sources → agent → destinations, with the external model shown unavailable for private data); timeline of steps with latency and route; the blocked step is a lime-tinted card containing "Why this was stopped" (rule, layer, OWASP with edition year, document score, judge, signature or "none", evidence quote); right column: approval card with parameters, rule, labels, agent's reason, bound hash, the two signature slots (Agent struck through, Compliance waiting), Deny and Approve, expiry.

**Management** (`#management`): organised by the questions a CISO or head of compliance asks, in this order. Each block says what it answers and what to do with it.

1. *Overview.* Posture ring with its definition ("share of the policy's protection that is switched on; not a risk score"), `N of M controls active`, and every deduction named with its amount. Five figures, no cards: requests (with the allowed / redacted / approval split), **blocked** and its share, approvals open with median decision time and expired count, **private → external** (0 is calm; above 0 a Breach pill and an alert bar), spent (external, local, compute seconds).
2. *Threats stopped* (is the layer working?). Line chart **Blocked per hour** over 24 h and ranked bars **What stopped them** (rules, with the OWASP category).
3. *Data protection* (is private data staying inside the bank?). **Where each data class went**: per class, requests answered by the local vs an external model; private classes show `0 to external` or a count; plus fields removed before leaving the gateway.
4. *Policy health* (has anything been weakened?). Controls table (id, one-line purpose, Rule/AI, setting, status, hits per hour, p95) with the REMOVED row, alert bar and last diff; policy at a glance (thresholds Block vs Redact, allowed models, budget rules); known attacks blocked (signature type, matches, reference, count); policy history; signature feed status.
5. *Cost* (what does it cost and who is near a limit?). Budgets per agent, team and session in USD, compute seconds and tokens, with **burn rate and the time the limit would be reached at the current pace**; local vs external split; requests blocked or rerouted by budget.
6. *Speed* (does it slow developers down?). Throughput and gateway p95 as two separate line charts (never one chart with two axes); **gateway overhead vs model time** (the layer's cost next to the model's); rule vs AI check time.
7. *Proof it works.* Test suite result (positive and negative passed, **missed attacks, false blocks**), `make test`, and OWASP LLM Top 10 coverage tiles (enforced / monitor only / uncovered, with the edition year). "N/10 categories have a passing test" is a note here, not a headline.

The "Demo: remove a control" button exists only in the key visual; the real UI changes when the policy file changes.

**What the numbers mean (shown in the UI, not only here).** Posture is configuration health: 100 minus the weight share of controls that are removed (full) or monitor-only (half), minus fixed penalties for a stale or failing signature feed, an unavailable AI check model and failing tests. It does not measure risk. OWASP coverage is derived from the tags of the controls that are active right now; it says "something enforces this category", and the test results are the evidence that it works.

**Chat** (`#chat`): one conversation box like a chat assistant, no separate modes. A **plus** next to the box opens a menu: upload a file, or attach an example client document. A message without a file is a prompt (one session is kept across messages, with a "New session" link); a message with a file is sent as an **untrusted client upload** and starts a KYC agent session. The thread shows your message (or the file chip and the start of its text) and under it the gateway's verdict in plain words (`Stopped before it reached the model`, `Answered by the local model`, `Held for a human`), a block in the lime-tinted box, and the facts that exist (rule, checked by rule or AI, code, OWASP with year, injection score, data class, route, time). For a file it summarises the agent's steps and offers **Open this session in Security**. The text box is locked while a file is attached, because the backend takes a single `text` field; the file is the message. Text files only for now (`.txt`, `.md`, `.csv`, `.json`, `.eml`, `.log`, up to 200 KB); anything else gets a message that says what to do. Files can also be dropped on the box. Example prompts sit under the box.

**States** (`#states`, a design reference): gateway not responding, empty list, loading skeleton, late data and the three connection states, invariant breach, hostile or very long text. Every panel implements these via the shared `Async` wrapper.

## 4b. Charts

Charts exist only where the data's job needs one: a trend over time (line, one series), a ranking of nominal items (bars), a split of a whole in two parts (stacked bars). Everything else is a figure or a table. Rules, from the data-viz method we follow:

- One accent plus greys. A single series is lime; in a ranking only the leader is lime and the rest grey (emphasis, not categories). Two series use white and grey, never lime next to white (they are too close under colour-blindness: tritan ΔE 6.9). Checked with the palette validator: lime↔grey ΔE ≈ 35, white↔grey ΔE ≈ 38, contrast ≥ 3:1 on `--ink`.
- Never two y-axes. Two measures of different scale are two charts.
- Thin marks: 2 px lines, bars no thicker than 24 px with a 4 px rounded data end, 2 px gap between touching fills, a surface ring on dots, a 10% wash under a line, hairline solid grid. No border around marks.
- A legend whenever there are two series; none for one. Direct label only the latest or the extreme value, never every point. Text uses text tokens, never the series colour.
- Every chart has a **table view** with the same numbers, a crosshair and tooltip on hover **and** on keyboard focus (arrow keys), and a text description for screen readers. Untrusted names (rules, classes) are rendered as text.
- Axis ends are rounded to clean numbers; an empty window shows a sentence, not an empty plot.

## 5. Task requirement coverage

Each row is something the task asks the dashboard or reporting to deliver, and where it is shown.

| Task requirement | Where |
|---|---|
| Dashboard shows controls, overall security posture, blocked threats, resource use and cost | Management: controls table, posture ring, blocked figure and chart, budgets |
| Reporting for security teams and for management | Security views; Management view |
| Central policy: thresholds (block vs redact), allowed models, budgets | Management: policy at a glance; setting column in controls |
| Rule-based and AI-based controls | Type column (Rule / AI) |
| Budgets for tokens, compute time and spend | Budgets: USD, compute seconds, tokens, per-session limits |
| Known historical attacks via an external signature feed | Known attacks blocked; signature feed status; signature and reference in "Why this was stopped" |
| Real-time metrics (blocked interactions, budget use) | Management figures and budget bars (SSE plus polling) |
| Exportable audit logs for threats, policy violations and usage | Export dialog: time, agent, session, decision, rule, OWASP, event types, JSONL or CSV, redaction notice |
| Test suite with positive and negative cases | Management: suite result, positive/negative, false blocks, missed attacks |
| Judges send ad-hoc prompts | Chat: Prompt and Document |
| Judges change config or feeds and see the effect live | Policy history and version, REMOVED scene, posture and OWASP update, diff |
| Performance telemetry | Management: throughput and gateway p95 over time, overhead vs model time, rule vs AI time |

Not a UI deliverable (tracked elsewhere): architecture diagram, sample policy file, test suite itself, PDF.

## 6. Scope changes against the UI plan

1. Colour semantics (blue / orange / red, green-yellow-red meters, red counter) and the light theme are **removed**; use section 3.
2. New: **Where the data went** map in the session detail (new task U5b). It is a read-only view over the session's audit events.
3. New: **Export dialog** with filters and format (replaces the simple export panel in U7).
4. New: **file attachments** in Chat through the plus menu (U11); there is no separate Document mode.
5. New: **Threats stopped** and **Data protection** charts (U8), **Known attacks**, **Policy at a glance** (U9), budget burn rate, speed charts and **missed attacks / false blocks** (U10).
6. New: **States** coverage (task U13).
7. Still out of scope: honeypot panel, session replay, follow mode, attack mode, a "re-run tests" button.

The backend contract gains the fields listed in the "Contract additions" block of Task 14 in the backend plan.
