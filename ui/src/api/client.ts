import type {
  ApprovalT, AttackStatusT, BudgetsT, ChatResult, ControlRow, ExportFilters, Metrics, OwaspT, PolicyT, PostureT,
  SessionDetailT, SessionFilters, SessionRow, SignaturesT, TestsT, TimeseriesT,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    let message = res.statusText || `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body?.error?.message ?? body?.detail ?? body?.error ?? JSON.stringify(body);
    } catch {
      /* keep the status text */
    }
    throw new ApiError(res.status, String(message));
  }
  return (await res.json()) as T;
}

function qs(params: Record<string, string | undefined>): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) u.set(k, v);
  const s = u.toString();
  return s ? `?${s}` : "";
}

export const api = {
  metrics: () => request<Metrics>("/metrics"),
  sessions: (f: SessionFilters = {}) => request<{ sessions: SessionRow[] }>(`/admin/sessions${qs({ ...f })}`),
  session: (id: string) => request<SessionDetailT>(`/admin/sessions/${encodeURIComponent(id)}`),
  approvals: (status: "pending" | "all" = "pending") => request<{ approvals: ApprovalT[] }>(`/admin/approvals${qs({ status })}`),
  decide: (id: string, approve: boolean, by = "compliance") =>
    request<ApprovalT>(`/admin/approvals/${encodeURIComponent(id)}/decide`, {
      method: "POST",
      body: JSON.stringify({ approve, by }),
    }),
  controls: () => request<{ controls: ControlRow[]; last_diff: string[] }>("/admin/controls"),
  posture: () => request<PostureT>("/admin/posture"),
  owasp: () => request<OwaspT>("/admin/owasp"),
  policy: () => request<PolicyT>("/admin/policy"),
  budgets: () => request<BudgetsT>("/admin/budgets"),
  signatures: () => request<SignaturesT>("/admin/signatures"),
  timeseries: (window = "24h") => request<TimeseriesT>(`/admin/timeseries${qs({ window })}`),
  tests: () => request<TestsT>("/admin/tests"),
  attackStatus: () => request<AttackStatusT>("/admin/demo/attack"),
  startAttack: () => request<AttackStatusT>("/admin/demo/attack", { method: "POST" }),
  chat: (body: { mode: "prompt" | "document"; text: string; session_id?: string; model?: string; question?: string;
                 file?: { name: string; content_type: string; content_base64: string } }) =>
    request<ChatResult>("/admin/chat", { method: "POST", body: JSON.stringify(body) }),
};

export function exportUrl(f: ExportFilters): string {
  return `/audit/export${qs({
    format: f.format, decision: f.decision, agent: f.agent, session: f.session, rule: f.rule,
    owasp: f.owasp, from: f.from, to: f.to, events: f.events,
  })}`;
}
