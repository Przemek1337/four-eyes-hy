import type { Metrics } from "../api/types";
import { fmtDuration, fmtUsd } from "../format";

function Kpi({ label, value, sub, hold, breach }: { label: string; value: string; sub?: string; hold?: boolean; breach?: boolean }) {
  return (
    <div className={hold ? "kpi hold" : "kpi"} role="group" aria-label={label}>
      <b>{value}{breach && <span className="badge badge-red kpi-breach">Breach</span>}</b>
      <span>{label}</span>
      {sub && <small>{sub}</small>}
    </div>
  );
}

/** Five figures a decision-maker uses. Lime marks what FourEyes holds: blocked requests and the private → external invariant. */
export function KpiRow({ metrics }: { metrics: Metrics }) {
  const d = metrics.by_decision;
  const n = (v: number) => v.toLocaleString("en-US");
  const breach = metrics.private_to_external > 0;
  const spent = metrics.cost.external_usd + metrics.cost.local_usd;
  const share = metrics.requests > 0 ? Math.round((d.BLOCK / metrics.requests) * 100) : 0;
  const approvalSub = [
    metrics.approval_median_s != null ? `median decision ${fmtDuration(metrics.approval_median_s)}` : "none decided yet",
    metrics.approvals_expired ? `${metrics.approvals_expired} expired` : null,
  ].filter(Boolean).join(" · ");
  return (
    <div className="kpis">
      <Kpi label="Requests" value={n(metrics.requests)} sub={`${n(d.ALLOW)} allowed · ${n(d.REDACT)} redacted · ${n(d.APPROVAL)} for approval`} />
      <Kpi label="Blocked" value={n(d.BLOCK)} hold sub={`${share}% of requests`} />
      <Kpi label="Approvals open" value={n(metrics.open_approvals)} sub={approvalSub} />
      <Kpi label="Private → external" value={n(metrics.private_to_external)} hold breach={breach}
           sub={breach ? "Private data reached an external model. This must stay at 0." : "private data sent to an external model"} />
      <Kpi label="Spent" value={fmtUsd(spent)} sub={`external ${fmtUsd(metrics.cost.external_usd)} · local ${fmtUsd(metrics.cost.local_usd)} · ${metrics.cost.compute_s.toFixed(1)} s compute`} />
    </div>
  );
}
