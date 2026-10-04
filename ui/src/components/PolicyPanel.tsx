import type { PolicyT } from "../api/types";
import { fmtTime } from "../format";
import { Badge } from "./Badge";

const eventTone = (e: string) => (e === "policy.rejected" ? "red" : e === "policy.reloaded" ? "green" : "gray");

/** What changed in the policy and when, and whether the signature feed is healthy. Rejections and feed errors are alerts. */
export function PolicyPanel({ policy }: { policy: PolicyT }) {
  const feed = policy.feed;
  return (
    <section className="subsec" aria-label="Policy and feed">
      <div className="pf">
        <div>
          <h3>Policy history</h3>
          <p className="sub">Version {policy.version}, profile {policy.profile}.</p>
          {policy.error && (
            <p role="alert" className="state state-error">
              The last policy change was rejected: {policy.error}. Still running {policy.version}.
            </p>
          )}
          {policy.history.length === 0 ? (
            <p className="state">No changes recorded yet.</p>
          ) : (
            <ol className="hist">
              {policy.history.map((h, i) => (
                <li key={i}>
                  <time>{fmtTime(h.ts)}</time>
                  <div>
                    <span className="row"><b>{h.version}</b> <Badge tone={eventTone(h.event)}>{h.event}</Badge></span>
                    {h.error && <div className="muted">{h.error}</div>}
                    {h.diff.slice(0, 5).map((d, j) => <div key={j}><code>{d}</code></div>)}
                    {h.diff.length > 5 && <div className="muted">+{h.diff.length - 5} more</div>}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
        <div>
          <h3>Signature feed</h3>
          <p className="sub">Known attacks from outside, reloaded on change.</p>
          <dl className="facts2">
            <div><dt>Version</dt><dd>{feed.version ?? "not loaded"}</dd></div>
            <div><dt>Signatures</dt><dd>{`${feed.count} signatures`}</dd></div>
            <div><dt>Last reload</dt><dd>{fmtTime(feed.last_reload)}</dd></div>
            <div><dt>Errors</dt><dd>{feed.error ? "see below" : "None"}</dd></div>
          </dl>
          {feed.error && <p role="alert" className="state state-error">{feed.error}</p>}
        </div>
      </div>
    </section>
  );
}
