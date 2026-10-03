import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { exportUrl } from "../api/client";

export const OWASP_IDS = Array.from({ length: 10 }, (_, i) => `LLM${String(i + 1).padStart(2, "0")}:2026`);

const EVENT_GROUPS = [
  { id: "decisions", label: "Decisions and threats" },
  { id: "policy", label: "Policy changes and violations" },
  { id: "usage", label: "Budget and resource use" },
] as const;

const RANGES = [
  { id: "all", label: "All time" },
  { id: "hour", label: "Last hour" },
  { id: "day", label: "Last 24 hours" },
  { id: "custom", label: "Custom range" },
] as const;

const iso = (v: string): string | undefined => {
  if (!v) return undefined;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString();
};

const FOCUSABLE = 'a[href], button:not(:disabled), input, select, textarea, [tabindex]:not([tabindex="-1"])';

/** Audit log export. Same filters as the API; the notice that content is redacted is part of the dialog. */
export function ExportDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [f, setF] = useState({ format: "jsonl" as "jsonl" | "csv", range: "all", from: "", to: "", agent: "", session: "", decision: "", rule: "", owasp: "" });
  const [events, setEvents] = useState<string[]>(EVENT_GROUPS.map((g) => g.id));
  const set = (patch: Partial<typeof f>) => setF((s) => ({ ...s, ...patch }));
  const panel = useRef<HTMLDivElement>(null);
  const opener = useRef<Element | null>(null);
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    opener.current = document.activeElement;
    panel.current?.focus();
    return () => (opener.current as HTMLElement | null)?.focus?.();
  }, [open]);

  if (!open) return null;

  const now = Date.now();
  const from = f.range === "hour" ? new Date(now - 3_600_000).toISOString()
    : f.range === "day" ? new Date(now - 86_400_000).toISOString()
    : f.range === "custom" ? iso(f.from) : undefined;
  const to = f.range === "custom" ? iso(f.to) : undefined;
  const allEvents = events.length === EVENT_GROUPS.length;
  const noEvents = events.length === 0;
  const href = exportUrl({
    format: f.format, decision: f.decision, agent: f.agent, session: f.session, rule: f.rule, owasp: f.owasp, from, to,
    events: allEvents ? undefined : events.join(","),
  });
  const toggleEvent = (id: string) => setEvents((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Escape") { e.stopPropagation(); onClose(); return; }
    if (e.key !== "Tab" || !panel.current) return;
    const items = Array.from(panel.current.querySelectorAll<HTMLElement>(FOCUSABLE));
    if (items.length === 0) return;
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement === panel.current)) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  };

  return (
    <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} ref={panel} onKeyDown={onKeyDown}>
        <h2 id={titleId}>Export audit log</h2>
        <p className="page-sub">Choose what to include. The same filters work on the API.</p>

        <div className="fg">
          <label>Time range
            <select value={f.range} onChange={(e) => set({ range: e.target.value })}>
              {RANGES.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
            </select>
          </label>
          <label>Agent<input value={f.agent} onChange={(e) => set({ agent: e.target.value })} placeholder="kyc-agent" /></label>
          {f.range === "custom" && (
            <>
              <label>From<input type="datetime-local" value={f.from} onChange={(e) => set({ from: e.target.value })} /></label>
              <label>To<input type="datetime-local" value={f.to} onChange={(e) => set({ to: e.target.value })} /></label>
            </>
          )}
          <label>Session<input value={f.session} onChange={(e) => set({ session: e.target.value })} placeholder="sess_7f3a" /></label>
          <label>Decision
            <select value={f.decision} onChange={(e) => set({ decision: e.target.value })}>
              {["", "ALLOW", "REDACT", "APPROVAL", "BLOCK"].map((d) => <option key={d} value={d}>{d || "All decisions"}</option>)}
            </select>
          </label>
          <label>Rule<input value={f.rule} onChange={(e) => set({ rule: e.target.value })} placeholder="authz.tools" /></label>
          <label>OWASP category
            <select value={f.owasp} onChange={(e) => set({ owasp: e.target.value })}>
              <option value="">Any category</option>
              {OWASP_IDS.map((id) => <option key={id} value={id}>{id}</option>)}
            </select>
          </label>
        </div>

        <fieldset>
          <legend>Events</legend>
          <div className="chk">
            {EVENT_GROUPS.map((g) => (
              <label key={g.id}><input type="checkbox" checked={events.includes(g.id)} onChange={() => toggleEvent(g.id)} /> {g.label}</label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend>Format</legend>
          <div className="seg" role="group" aria-label="Format">
            <button type="button" aria-pressed={f.format === "jsonl"} onClick={() => set({ format: "jsonl" })}>JSONL</button>
            <button type="button" aria-pressed={f.format === "csv"} onClick={() => set({ format: "csv" })}>CSV</button>
          </div>
          <p className="note">JSONL is raw events for a SIEM or scripts. CSV opens in Excel for compliance.</p>
        </fieldset>

        <p className="redact-note">Export contains redacted content only</p>
        <code className="endpoint">GET {href}</code>
        {noEvents && <p role="alert" className="state state-error">Pick at least one kind of event to export.</p>}

        <div className="dlg-actions">
          <button className="btn" onClick={onClose}>Cancel</button>
          {noEvents
            ? <span className="btn primary disabled" aria-disabled="true">Download</span>
            : <a className="btn primary" href={href} download onClick={onClose}>Download</a>}
        </div>
      </div>
    </div>
  );
}
