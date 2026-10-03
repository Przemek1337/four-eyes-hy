import type { ApprovalT, AuditEvent, SessionRow } from "../api/types";

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

export const fx = { session, approval, decision };
