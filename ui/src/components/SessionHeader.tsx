import type { SessionDetailT } from "../api/types";
import { fmtTime } from "../format";

export function SessionHeader({ session, headline, taintedFrom }: {
  session: SessionDetailT["session"];
  headline: string;
  taintedFrom: number | null;
}) {
  const scope = Object.entries(session.scope).map(([k, v]) => `${k}=${v}`).join(", ");
  const waiting = session.pending_approvals;
  return (
    <header>
      <h1 className="page-title tl-title">{headline}</h1>
      <div className="meta">
        <span>{session.agent}</span>
        {session.client && <span>{session.client}</span>}
        <span>{session.session_id}</span>
        <span>Started {fmtTime(session.started)}</span>
        <span>{session.steps} steps</span>
        {scope && <span>Scope {scope}</span>}
        {session.task && <span>Task: {session.task}</span>}
      </div>
      <div className="labels">
        {taintedFrom != null && <span className="lab dirty">{`untrusted since step ${taintedFrom}`}</span>}
        <span className="lab">{session.data_class}</span>
        {session.blocked_count > 0 && <span className="lab solid">{`${session.blocked_count} action${session.blocked_count === 1 ? "" : "s"} stopped`}</span>}
        {waiting > 0 && <span className="lab hold">{`${waiting} waiting`}</span>}
      </div>
    </header>
  );
}
