import { api } from "../api/client";
import { Async } from "../components/Async";
import { DataProtectionPanel } from "../components/DataProtectionPanel";
import { KpiRow } from "../components/KpiRow";
import { OwaspPanel } from "../components/OwaspPanel";
import { DeductionLine, PosturePanel } from "../components/PosturePanel";
import { ThreatsPanel } from "../components/ThreatsPanel";
import { usePolling } from "../hooks/usePolling";

export function ManagementView() {
  const metrics = usePolling(api.metrics, []);
  const posture = usePolling(api.posture, []);
  const owasp = usePolling(api.owasp, []);
  const series = usePolling(() => api.timeseries("24h"), []);
  const top = {
    data: metrics.data && posture.data ? { m: metrics.data, p: posture.data } : null,
    error: metrics.error ?? posture.error,
    loading: metrics.loading || posture.loading,
  };
  const removed = posture.data?.breakdown.filter((b) => b.note === "removed") ?? [];
  const breach = (metrics.data?.private_to_external ?? 0) > 0;
  return (
    <section aria-label="Management view">
      <h1 className="page-title">Management</h1>
      <p className="page-sub">
        Is the control layer working, is data safe, and what does it cost?{metrics.data ? ` Policy ${metrics.data.policy_version}.` : ""}
      </p>

      {removed.length > 0 && (
        <div className="alertbar" role="alert">
          <span className="badge badge-red">Removed</span>
          <div>
            <b>{removed.map((r) => r.item).join(", ")} {removed.length === 1 ? "was" : "were"} removed from the policy.</b>
            <span>Posture dropped by {Math.abs(removed.reduce((s, r) => s + r.delta, 0))}. Put it back in the policy file to restore it.</span>
          </div>
        </div>
      )}
      {breach && (
        <div className="alertbar" role="alert">
          <span className="badge badge-red">Breach</span>
          <div>
            <b>Private data reached an external model.</b>
            <span>This count must stay at 0. Open the sessions that sent it.</span>
          </div>
        </div>
      )}

      <Async state={top}>
        {({ m, p }) => (
          <>
            <div className="top">
              <PosturePanel posture={p} />
              <div>
                <KpiRow metrics={m} />
                <DeductionLine posture={p} />
              </div>
            </div>
            <ThreatsPanel metrics={m} series={series.data} />
            <DataProtectionPanel metrics={m} />
          </>
        )}
      </Async>
      <Async state={owasp}>{(o) => <OwaspPanel owasp={o} />}</Async>
    </section>
  );
}
