import type { ApprovalT, AuditEvent, FlowT, Metrics, OwaspT, PostureT, SessionRow } from "../api/types";

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
  ...over,
});

export const posture = (over: Partial<PostureT> = {}): PostureT => ({
  score: 90, max: 100,
  breakdown: [{ item: "dlp.redact_inflight", delta: -10, note: "removed" }],
  formula: "score = 100 minus control weights for removed or monitor-only controls, minus penalties", ...over,
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

export const fx = { session, approval, decision, flow, metrics, posture, owasp };
