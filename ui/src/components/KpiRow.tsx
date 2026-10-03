import type { Metrics } from "../api/types";
import { fmtUsd } from "../format";

function Kpi({ label, value, sub, hold, breach }: { label: string; value: string; sub?: string; hold?: boolean; breach?: boolean }) {
  return (
    <div className={hold ? "kpi hold" : "kpi"} role="group" aria-label={label}>
      <b>{value}{breach && <span className="badge badge-red kpi-breach">Breach</span>}</b>
      <span>{label}</span>
      {sub && <small>{sub}</small>}
    </div>
  );
}

/** Eight plain figures, no cards. Lime marks what FourEyes holds: blocked actions and the private → external invariant. */
export function KpiRow({ metrics }: { metrics: Metrics }) {
  const d = metrics.by_decision;
  const n = (v: number) => v.toLocaleString("en-US");
  const breach = metrics.private_to_external > 0;
  const spent = metrics.cost.external_usd + metrics.cost.local_usd;
  return (
    <div className="kpis">
      <Kpi label="Requests" value={n(metrics.requests)} />
      <Kpi label="Allowed" value={n(d.ALLOW)} />
      <Kpi label="Redacted" value={n(d.REDACT)} />
      <Kpi label="Sent for approval" value={n(d.APPROVAL)} />
      <Kpi label="Blocked" value={n(d.BLOCK)} hold />
      <Kpi label="Approvals open" value={n(metrics.open_approvals)} />
      <Kpi label="Private → external" value={n(metrics.private_to_external)} hold breach={breach}
           sub={breach ? "Private data reached an external model. This must stay at 0." : undefined} />
      <Kpi label="Spent" value={fmtUsd(spent)} sub={`external ${fmtUsd(metrics.cost.external_usd)} · local ${fmtUsd(metrics.cost.local_usd)} · ${metrics.cost.compute_s.toFixed(1)} s compute`} />
    </div>
  );
}
