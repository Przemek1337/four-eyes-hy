import type { ApprovalT } from "../api/types";

function target(a: ApprovalT): string {
  const to = a.args?.to ?? a.args?.recipient;
  return typeof to === "string" ? `${a.tool} to ${to}` : a.tool;
}

/** Queue bar: the one place on the list that asks for a human. Lime outline only when something waits. */
export function ApprovalQueue({ approvals, onOpen }: { approvals: ApprovalT[]; onOpen: (sessionId: string) => void }) {
  const first = approvals[0];
  const n = approvals.length;
  return (
    <section className={n > 0 ? "queue waiting" : "queue"} aria-label={`Pending approvals (${n})`}>
      {first ? (
        <>
          <span className="dot" aria-hidden="true" />
          <div className="txt">
            <b>{n === 1 ? "1 action waiting for compliance" : `${n} actions waiting for compliance`}</b>
            <span>{target(first)} · {first.session_id}{n > 1 ? ` · and ${n - 1} more` : ""}</span>
          </div>
          <button className="btn-sm go" onClick={() => onOpen(first.session_id)}>Review</button>
        </>
      ) : (
        <p className="state">No approvals waiting.</p>
      )}
    </section>
  );
}
