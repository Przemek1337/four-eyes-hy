import type { SessionFilters, SessionRow } from "../api/types";
import { fmtTime } from "../format";
import { DecisionPill, StatusMark } from "./Badge";

const CLASSES = ["", "public", "personal_data", "bank_secret"];
const QUICK = [
  { label: "All", decision: "" },
  { label: "Blocked", decision: "BLOCK" },
  { label: "Needs approval", decision: "APPROVAL" },
];

export function SessionList({ rows, onSelect, filters, onFilters }: {
  rows: SessionRow[];
  onSelect: (id: string) => void;
  filters: SessionFilters;
  onFilters: (f: SessionFilters) => void;
}) {
  const set = (patch: SessionFilters) => onFilters({ ...filters, ...patch });
  const decision = filters.decision ?? "";
  return (
    <section aria-label="Sessions">
      <div className="tools">
        {QUICK.map((q) => (
          <button key={q.label} className="chip" aria-pressed={decision === q.decision} onClick={() => set({ decision: q.decision })}>
            {q.label}
          </button>
        ))}
        <input aria-label="Agent" placeholder="Agent" value={filters.agent ?? ""} onChange={(e) => set({ agent: e.target.value })} />
        <input aria-label="Rule" placeholder="Rule" value={filters.rule ?? ""} onChange={(e) => set({ rule: e.target.value })} />
        <select aria-label="Data class" value={filters.data_class ?? ""} onChange={(e) => set({ data_class: e.target.value })}>
          {CLASSES.map((c) => <option key={c} value={c}>{c || "Any class"}</option>)}
        </select>
      </div>
      {rows.length === 0 ? (
        <p className="state">No sessions match.</p>
      ) : (
        <div className="stable">
          <div className="srow head" aria-hidden="true">
            <span>Session</span><span>Agent</span><span className="hide-s">Client</span><span>Status</span>
            <span>Last decision</span><span className="hide-s">Steps</span><span className="hide-s">Started</span>
          </div>
          {rows.map((r) => (
            <div key={r.session_id} className="srow body" onClick={() => onSelect(r.session_id)}>
              <button className="link" onClick={(e) => { e.stopPropagation(); onSelect(r.session_id); }}>{r.session_id}</button>
              <span className="muted">{r.agent}</span>
              <span className="hide-s">{r.client ?? "–"}</span>
              <StatusMark status={r.status} />
              <span><DecisionPill decision={r.last_decision} /></span>
              <span className="muted hide-s">{r.steps}</span>
              <span className="muted hide-s">{fmtTime(r.started)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
