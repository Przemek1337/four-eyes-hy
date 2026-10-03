export type Decision = "ALLOW" | "REDACT" | "APPROVAL" | "BLOCK";

export interface Stat { count: number; p50: number; p95: number }
export interface Latency {
  controls: Record<string, Stat>;
  layers: Record<string, Stat>;
  gateway: Stat;
  upstream: Stat;
  upstream_p95_ms?: number;
}
export interface FeedStatus { version: string | null; count: number; last_reload: number | null; error: string | null; source: string | null }

export interface Metrics {
  requests: number;
  by_decision: Record<Decision, number>;
  open_approvals: number;
  by_class: Record<string, number>;
  by_upstream_type: { local: number; external: number };
  private_to_external: number;
  policy_version: string;
  latency: Latency;
  cost: { local_usd: number; external_usd: number; compute_s: number };
  feed: FeedStatus;
  throughput_per_min?: number;
}

export interface SessionRow {
  session_id: string;
  agent: string;
  client?: string | null;
  started: number;
  steps: number;
  labels: string[];
  data_class: string;
  status: "clean" | "untrusted" | "high_risk";
  last_decision: Decision | null;
  blocked_count: number;
  pending_approvals: number;
}

export interface RouteInfo {
  allowed: string[];
  chosen: string;
  model: string;
  router: string;
  rerouted_from: string | null;
  fallback: boolean;
}

export interface AuditEvent {
  event: string;
  ts: string;
  session_id: string;
  decision_id?: string;
  kind?: "model" | "tool";
  action?: string;
  resource?: string;
  decision?: Decision;
  rule?: string;
  reason?: string;
  layer?: "det" | "ai";
  code?: string | null;
  owasp?: string[];
  signature_id?: string | null;
  reference?: string | null;
  labels?: string[];
  data_class?: string;
  latency_ms?: number;
  gateway_ms?: number;
  upstream_ms?: number;
  timings?: { control: string; phase: string; ms: number; outcome: string }[];
  route?: RouteInfo | null;
  anonymization?: string | null;
  alerts?: ({ kind: string } & Record<string, unknown>)[];
  detail?: Record<string, unknown>;
  content?: string;
  evidence?: string;
  redaction?: string;
  injection_score?: number | null;
  judge?: { score: number; reason: string } | null;
  from?: string;
  to?: string;
  label?: string;
  source?: string;
  policy_version?: string;
}

export interface JudgeInfo { consistent: boolean; score: number; reason: string }

export interface ApprovalT {
  id: string;
  hash: string;
  session_id: string;
  agent_id: string;
  tool: string;
  args: Record<string, unknown>;
  rule: string;
  reason: string;
  labels: string[];
  data_class: string;
  judge: JudgeInfo | null;
  supplied_reason: string | null;
  created: number;
  expires_at: number;
  status: "pending" | "approved" | "denied" | "consumed";
  decided_by: string | null;
  decided_at: number | null;
}

/** Read-only "where the data went" view, derived by the gateway from the session's audit events. */
export interface FlowT {
  sources: { name: string; detail: string; label: string }[];
  agent: { name: string; model: string; labels: string[]; labels_since_step: number | null };
  destinations: { name: string; detail: string; outcome: "passed" | "blocked" | "held" | "unavailable" }[];
}

export interface SessionDetailT {
  session: SessionRow & { scope: Record<string, string>; task: string | null };
  events: AuditEvent[];
  approvals: ApprovalT[];
  flow?: FlowT;
}

export interface ControlRow {
  id: string;
  description: string;
  type: "det" | "ai";
  status: "active" | "monitor" | "REMOVED";
  mode: string | null;
  setting?: string;
  params: Record<string, unknown>;
  owasp: string[];
  hits_1h: number;
  p95_ms: number;
  weight: number;
}

export interface PostureT { score: number; max: number; breakdown: { item: string; delta: number; note: string }[]; formula?: string }

export interface OwaspT {
  edition: string;
  tested: string;
  categories: { id: string; name: string; status: "enforced" | "monitor_only" | "uncovered"; controls: string[]; blocks: number; note: string }[];
}

export interface LabelValue { label: string; value: string }

export interface PolicyT {
  version: string;
  profile: string;
  error: string | null;
  history: { version: string; ts: number; event: string; diff: string[]; error?: string }[];
  feed: FeedStatus;
  summary?: { block_or_redact: LabelValue[]; models: LabelValue[]; budgets: LabelValue[] };
}

export interface BudgetRow { pct: number | null; level: "ok" | "warn" | "over" }
export interface BudgetsT {
  agents: (BudgetRow & {
    agent: string; team: string | null; usd_used: number; usd_limit: number | null;
    compute_used: number; compute_limit: number | null; tokens_used?: number;
  })[];
  teams: (BudgetRow & { team: string; usd_used: number; usd_limit: number | null })[];
  blocked_by_budget: number;
  fallbacks: number;
  session_limits?: { max_tokens: number; max_steps: number; busiest: { tokens: number; steps: number }; stopped_by_limit: number };
}

export interface SignaturesT {
  feed: FeedStatus;
  hits: { type: string; matches: string; reference: string; signature_id: string | null; blocked: number }[];
}

export interface TestsT {
  passed: number;
  failed: number;
  positive: { passed: number; failed: number };
  negative: { passed: number; failed: number };
  by_owasp: Record<string, { passed: number; failed: number }>;
  false_blocks: number;
  missed_attacks: number;
  ran_at: number | null;
  policy_version: string | null;
}

export interface ChatResult {
  session_id: string;
  decision: Decision;
  rule: string | null;
  layer: string | null;
  code: string | null;
  owasp: string[];
  data_class: string | null;
  route: { type: string; model: string; router: string; rerouted_from: string | null } | null;
  latency_ms: number | null;
  injection_score: number | null;
  reply: string | null;
  approval_id: string | null;
  message: string;
  steps: { n: number; tool: string; args: Record<string, unknown>; outcome: string; code: string | null; approval_id: string | null }[];
}

export interface SessionFilters { agent?: string; decision?: string; data_class?: string; rule?: string }
export interface ExportFilters {
  format: "jsonl" | "csv";
  decision?: string; agent?: string; session?: string; rule?: string; owasp?: string; from?: string; to?: string;
  /** comma list of event groups: decisions, policy, usage */
  events?: string;
}
