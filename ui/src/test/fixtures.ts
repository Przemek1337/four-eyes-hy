import type { ApprovalT, AuditEvent, ControlRow, FlowT, Metrics, OwaspT, PolicyT, PostureT, SessionRow, SignaturesT, TimeseriesT } from "../api/types";

export const session = (over: Partial<SessionRow> = {}): SessionRow => ({
  session_id: "a41f", agent: "kyc-agent", client: "Nowak Logistics", started: 1_760_000_000, steps: 5, labels: ["untrusted", "high_risk"],
  data_class: "bank_secret", status: "high_risk", last_decision: "APPROVAL", blocked_count: 1, pending_approvals: 1, ...over,
});

export const approval = (over: Partial<ApprovalT> = {}): ApprovalT => ({
  id: "ap1", hash: "a1f3c9d2e4b5f60718293a4b5c6d7e8f", session_id: "a41f", agent_id: "kyc-agent", tool: "send_email",
  args: { to: "kyc-verify@external.example", subject: "docs", body: "client data" }, rule: "flow.untrusted",
  reason: "egress action in a untrusted session (strict profile)", labels: ["high_risk", "untrusted"], data_class: "bank_secret",
  judge: { consistent: false, score: 0.91, reason: "recipient outside the bank is inconsistent with the case task" },
  supplied_reason: "forward documents for verification", created: 1_760_000_000, expires_at: 1_760_000_900,
  status: "pending", decided_by: null, decided_at: null, ...over,
});

export const decision = (over: Partial<AuditEvent> = {}): AuditEvent => ({
  event: "decision", ts: "2026-10-03T14:02:11Z", session_id: "a41f", decision_id: "d1", kind: "tool", action: "tool:entities_get",
  resource: "entities_get", decision: "ALLOW", rule: "pipeline", reason: "", layer: "det", code: null, owasp: [], labels: [],
  data_class: "public", latency_ms: 3, gateway_ms: 2, upstream_ms: 1, route: null, alerts: [], detail: {}, ...over,
});

export const flow = (): FlowT => ({
  sources: [
    { name: "User request", detail: "Verify client Nowak Logistics", label: "trusted" },
    { name: "client_upload.pdf", detail: "Hidden instruction on page 3", label: "untrusted" },
  ],
  agent: { name: "kyc-agent", model: "qwen2.5:7b", labels: ["untrusted", "personal_data"], labels_since_step: 2 },
  destinations: [
    { name: "Local model", detail: "Allowed for personal_data", outcome: "passed" },
    { name: "External model", detail: "Public data only", outcome: "unavailable" },
    { name: "entities_submit", detail: "No sanctions screening", outcome: "blocked" },
    { name: "send_email", detail: "onboarding-docs@kyc-verify.example", outcome: "held" },
  ],
});

export const metrics = (over: Partial<Metrics> = {}): Metrics => ({
  requests: 1284,
  by_decision: { ALLOW: 1102, REDACT: 61, APPROVAL: 3, BLOCK: 118 },
  open_approvals: 1,
  by_class: { public: 800, personal_data: 400, bank_secret: 84 },
  by_upstream_type: { local: 1100, external: 184 },
  private_to_external: 0,
  policy_version: "v4",
  latency: {
    controls: { "sig.feed": { count: 100, p50: 0.4, p95: 1.2 }, "sem.prompt_injection": { count: 100, p50: 16, p95: 24 } },
    layers: { det: { count: 400, p50: 1, p95: 3 }, ai: { count: 120, p50: 100, p95: 140 } },
    gateway: { count: 1284, p50: 6, p95: 18 },
    upstream: { count: 1284, p50: 410, p95: 1200 },
  },
  cost: { local_usd: 0, external_usd: 0.84, compute_s: 42.3 },
  feed: { version: "2026.10.03", count: 7, last_reload: 1_760_000_000, error: null, source: "./feeds/signatures.json" },
  top_blockers: [
    { rule: "sig.feed", owasp: ["LLM01:2026"], blocked: 44 },
    { rule: "flow.untrusted", owasp: ["LLM01:2026", "LLM03:2026"], blocked: 31 },
    { rule: "authz.tools", owasp: ["LLM03:2026"], blocked: 22 },
  ],
  routing: [
    { data_class: "public", local: 320, external: 180 },
    { data_class: "personal_data", local: 400, external: 0 },
    { data_class: "bank_secret", local: 84, external: 0 },
  ],
  redacted_fields: 61,
  approval_median_s: 138,
  approvals_expired: 0,
  ...over,
});

export const posture = (over: Partial<PostureT> = {}): PostureT => ({
  score: 90, max: 100,
  breakdown: [{ item: "dlp.redact_inflight", delta: -10, note: "removed" }],
  formula: "score = 100 minus control weights for removed or monitor-only controls, minus penalties",
  controls_active: 14, controls_total: 15, ...over,
});

export const owasp = (over: Partial<OwaspT> = {}): OwaspT => ({
  edition: "2026", tested: "10/10",
  categories: [
    { id: "LLM01:2026", name: "Prompt Injection", status: "enforced", controls: ["flow.untrusted", "sig.feed"], blocks: 41, note: "" },
    { id: "LLM02:2026", name: "Sensitive Information Disclosure", status: "monitor_only", controls: ["log.redact"], blocks: 0, note: "" },
    { id: "LLM07:2026", name: "Misinformation", status: "uncovered", controls: [], blocks: 0, note: "no grounding control in this policy" },
  ],
  ...over,
});

export const timeseries = (over: Partial<TimeseriesT> = {}): TimeseriesT => ({
  bucket_s: 3600,
  points: [3, 5, 2, 0, 1, 4, 12, 7, 3, 2, 6, 9].map((blocked, i) => ({
    ts: 1_760_000_000 + i * 3600, requests: 60 + i * 3, blocked, approval: i % 4 === 0 ? 1 : 0, redact: 4, gateway_p95_ms: 14 + (i % 5),
  })),
  ...over,
});

export const controls = (): ControlRow[] => [
  { id: "auth.agent_key", description: "Without a valid agent key nothing runs.", type: "det", status: "active", mode: "enforce", setting: "enforce", params: {}, owasp: ["LLM03:2026"], hits_1h: 2, p95_ms: 0.05, weight: 15 },
  { id: "sem.prompt_injection", description: "A classifier scores prompts and documents.", type: "ai", status: "monitor", mode: "enforce", setting: "block above 0.8",
    params: { prompts: { block_above: 0.8, log_above: 0.5 } }, owasp: ["LLM01:2026"], hits_1h: 7, p95_ms: 24, weight: 10 },
  { id: "dlp.redact_inflight", description: "Redacts secrets and unneeded fields.", type: "det", status: "REMOVED", mode: null, params: {}, owasp: ["LLM02:2026"], hits_1h: 0, p95_ms: 0, weight: 6 },
];

export const policy = (over: Partial<PolicyT> = {}): PolicyT => ({
  version: "v4", profile: "strict", error: null,
  history: [
    { version: "v4", ts: 1_760_000_300, event: "policy.reloaded", diff: ["~ profile: 'strict' -> 'relaxed'", "- controls.dlp.redact_inflight"] },
    { version: "v3", ts: 1_760_000_200, event: "policy.rejected", diff: [], error: "unknown control 'made.up'" },
    { version: "v3", ts: 1_760_000_100, event: "policy.loaded", diff: [] },
  ],
  feed: { version: "2026-10-03.1", count: 7, last_reload: 1_760_000_050, error: null, source: "./feeds/signatures.json" },
  summary: {
    block_or_redact: [{ label: "Prompt injection", value: "block above 0.8, log above 0.5" }, { label: "Secrets and personal data", value: "redact in flight and in logs" }],
    models: [{ label: "Local · qwen2.5:7b", value: "all data classes" }, { label: "External", value: "public data only" }],
    budgets: [{ label: "kyc-agent", value: "$2.00 and 600 compute s a day" }, { label: "Session", value: "20,000 tokens, 20 steps" }],
  },
  ...over,
});

export const signatures = (): SignaturesT => ({
  feed: { version: "2026.10.03", count: 7, last_reload: 1_760_000_050, error: null, source: "./feeds/signatures.json" },
  hits: [
    { type: "pickle_opcode", matches: "os.system, subprocess.Popen in model files", reference: "Malicious pickle models on public hubs (2024)", signature_id: "SIG-PKL-001", blocked: 3 },
    { type: "url_pattern", matches: "Image or link to a domain outside the allowlist", reference: "EchoLeak, CVE-2025-32711", signature_id: null, blocked: 2 },
  ],
});

export const fx = { session, approval, decision, flow, metrics, posture, owasp, timeseries, controls, policy, signatures };
