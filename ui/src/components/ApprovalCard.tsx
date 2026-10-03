import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ApprovalT } from "../api/types";
import { fmtTime, shortHash } from "../format";

const outcomeText = (a: ApprovalT): string =>
  a.status === "approved" ? `Approved by ${a.decided_by ?? "compliance"}`
  : a.status === "denied" ? `Denied by ${a.decided_by ?? "compliance"}`
  : a.status === "consumed" ? `Used (approved by ${a.decided_by ?? "compliance"})`
  : "";

/** The four-eyes moment: the agent cannot sign, a human can. The safe action (Deny) is the primary button. */
export function ApprovalCard({ approval, onDecided }: { approval: ApprovalT; onDecided?: (a: ApprovalT) => void }) {
  const [current, setCurrent] = useState(approval);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  useEffect(() => {
    setCurrent(approval);
  }, [approval]);

  const decide = async (approve: boolean) => {
    if (inFlight.current) return; // one decision per click burst
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.decide(current.id, approve);
      setCurrent(updated);
      onDecided?.(updated);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  const pending = current.status === "pending";
  const approved = current.status === "approved" || current.status === "consumed";
  const params = Object.entries(current.args);
  return (
    <section className="review" aria-label="Approval card">
      <h2>Compliance needs to review this action</h2>
      <p className="lead">No critical action runs on an agent’s word alone.</p>
      <dl className="what">
        <div><dt>Action</dt><dd className="mono">{current.tool}</dd></div>
        {params.map(([k, v]) => (
          <div key={k}><dt>{k}</dt><dd className="mono">{typeof v === "string" ? v : JSON.stringify(v)}</dd></div>
        ))}
        <div><dt>Why flagged</dt><dd>{current.judge
          ? `${current.judge.consistent ? "Consistent" : "Inconsistent"} with the task (${current.judge.score.toFixed(2)}): ${current.judge.reason}`
          : current.reason}</dd></div>
        <div><dt>Rule</dt><dd className="mono">{current.rule}</dd></div>
        {!current.judge && <div><dt>AI judge</dt><dd>not run</dd></div>}
        <div><dt>Session labels</dt><dd>{[...current.labels, current.data_class].join(", ")}</dd></div>
        {current.supplied_reason && <div><dt>Agent’s reason</dt><dd>“{current.supplied_reason}”</dd></div>}
        <div><dt>Bound to</dt><dd className="mono">{`sha256 ${shortHash(current.hash)}`}</dd></div>
      </dl>
      <div className="sigs">
        <div className="sig no"><span className="who">Agent</span><span className="state">Can’t approve its own action.</span></div>
        <div className={pending ? "sig wait" : approved ? "sig done" : "sig denied"}>
          <span className="who">Compliance</span>
          {pending ? <span className="dots" aria-hidden="true"><i /><i /></span> : null}
          <span className="state">{pending ? "Needs a second pair of eyes" : outcomeText(current)}</span>
        </div>
      </div>
      {pending && (
        <div className="actions">
          <button className="btn primary" disabled={busy} onClick={() => void decide(false)}>Deny</button>
          <button className="btn" disabled={busy} onClick={() => void decide(true)}>Approve</button>
        </div>
      )}
      {error && <p role="alert" className="state state-error">{error}</p>}
      <p className="fine">Approves exactly these parameters, once · expires {fmtTime(current.expires_at)}</p>
    </section>
  );
}
