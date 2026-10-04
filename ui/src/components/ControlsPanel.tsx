import type { ControlRow } from "../api/types";
import { fmtMs } from "../format";
import { Badge } from "./Badge";

const compact = (p: Record<string, unknown>): string => {
  const s = JSON.stringify(p);
  return s.length > 140 ? `${s.slice(0, 140)}…` : s;
};

function Status({ status }: { status: ControlRow["status"] }) {
  if (status === "REMOVED") return <Badge tone="red">Removed</Badge>;
  return <span className={status === "monitor" ? "cs mon" : "cs"}>{status === "monitor" ? "Monitor only" : "Active"}</span>;
}

/** Read-only. The policy file is the source of truth. A removed control is struck through with a lime pill. */
export function ControlsPanel({ controls, lastDiff }: { controls: ControlRow[]; lastDiff: string[] }) {
  return (
    <section className="subsec" aria-label="Controls">
      <h3>Controls</h3>
      <p className="sub">Read only. The policy file decides what runs.</p>
      <div className="table-scroll">
        <table className="ctab">
          <thead>
            <tr><th>Control</th><th>Type</th><th>Setting</th><th>Status</th><th>OWASP</th><th>Hits, 1 h</th><th>p95</th></tr>
          </thead>
          <tbody>
            {controls.map((c) => (
              <tr key={c.id} className={c.status === "REMOVED" ? "removed" : undefined}>
                <td><code className={c.status === "REMOVED" ? "struck" : undefined}>{c.id}</code><div className="muted">{c.description}</div></td>
                <td>
                  <span>{c.type === "ai" ? "AI" : "Rule"}</span>
                  {c.model && (
                    <div className="muted"><code>{c.model}</code>{c.model_status === "down" && <> <Badge tone="red">Down</Badge></>}</div>
                  )}
                </td>
                <td>
                  {c.status === "REMOVED" ? <span className="muted">removed</span> : (
                    <>
                      <span>{c.setting ?? c.mode ?? "–"}</span>
                      {!c.setting && Object.keys(c.params).length > 0 && <div className="muted"><code>{compact(c.params)}</code></div>}
                    </>
                  )}
                </td>
                <td><Status status={c.status} /></td>
                <td><div className="tags">{c.owasp.map((t) => <span key={t} className="tag-sm">{t}</span>)}</div></td>
                <td className="num">{c.status === "REMOVED" ? "–" : c.hits_1h}</td>
                <td className="num">{c.status === "REMOVED" ? "–" : fmtMs(c.p95_ms)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h4 className="lastchange">Last policy change</h4>
      {lastDiff.length === 0 ? (
        <p className="state">No changes since the gateway started.</p>
      ) : (
        <pre className="diff">{lastDiff.join("\n")}</pre>
      )}
    </section>
  );
}
