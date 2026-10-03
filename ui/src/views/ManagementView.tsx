import { api } from "../api/client";
import { Async } from "../components/Async";
import { BudgetsPanel } from "../components/BudgetsPanel";
import { ControlsPanel } from "../components/ControlsPanel";
import { DataProtectionPanel } from "../components/DataProtectionPanel";
import { GlanceList } from "../components/GlanceList";
import { KnownAttacks } from "../components/KnownAttacks";
import { KpiRow } from "../components/KpiRow";
import { OwaspPanel } from "../components/OwaspPanel";
import { PolicyGlance } from "../components/PolicyGlance";
import { PolicyPanel } from "../components/PolicyPanel";
import { SpeedPanel } from "../components/SpeedPanel";
import { Tabs, type TabDef } from "../components/Tabs";
import { TestsPanel } from "../components/TestsPanel";
import { DeductionLine, PosturePanel } from "../components/PosturePanel";
import { ThreatsPanel } from "../components/ThreatsPanel";
import { usePolling } from "../hooks/usePolling";
import { buildSummaries, SECTION_TITLES, type TabId } from "../managementSummary";
import { useState } from "react";

export function ManagementView() {
  const [tab, setTab] = useState<TabId>("overview");
  const metrics = usePolling(api.metrics, []);
  const posture = usePolling(api.posture, []);
  const owasp = usePolling(api.owasp, []);
  const series = usePolling(() => api.timeseries("24h"), []);
  const controls = usePolling(api.controls, []);
  const policy = usePolling(api.policy, []);
  const signatures = usePolling(api.signatures, []);
  const budgets = usePolling(api.budgets, []);
  const tests = usePolling(api.tests, []);
  const top = {
    data: metrics.data && posture.data ? { m: metrics.data, p: posture.data } : null,
    error: metrics.error ?? posture.error,
    loading: metrics.loading || posture.loading,
  };
  // A control counts as removed if the controls table says so or the posture breakdown does.
  const removedIds = new Set<string>([
    ...(controls.data?.controls.filter((c) => c.status === "REMOVED").map((c) => c.id) ?? []),
    ...(posture.data?.breakdown.filter((b) => b.note === "removed").map((b) => b.item) ?? []),
  ]);
  const removed = [...removedIds];
  const dropped = Math.abs(posture.data?.breakdown.filter((b) => b.note === "removed").reduce((sum, b) => sum + b.delta, 0) ?? 0);
  const breach = (metrics.data?.private_to_external ?? 0) > 0;
  const summaries = buildSummaries({
    metrics: metrics.data, series: series.data, controls: controls.data?.controls, policy: policy.data,
    budgets: budgets.data, tests: tests.data, owasp: owasp.data,
  });
  const tabs: TabDef<TabId>[] = [
    { id: "overview", label: "Overview" },
    { id: "threats", label: "Threats" },
    { id: "data", label: "Data", attention: summaries.data?.attention },
    { id: "policy", label: "Policy", attention: summaries.policy?.attention },
    { id: "cost", label: "Cost", attention: summaries.cost?.attention },
    { id: "speed", label: "Speed" },
    { id: "proof", label: "Proof", attention: summaries.proof?.attention },
  ];
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
            <b>{removed.join(", ")} {removed.length === 1 ? "was" : "were"} removed from the policy.</b>
            <span>{dropped > 0 ? `Posture dropped by ${dropped}. ` : ""}Put it back in the policy file to restore it.</span>
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

      <Tabs tabs={tabs} value={tab} onChange={setTab} label="Management sections" />
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="tabpanel">
        {tab === "overview" && (
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
              </>
            )}
          </Async>
        )}
        {tab === "overview" && <GlanceList summaries={summaries} onOpen={setTab} loading={metrics.loading || controls.loading || budgets.loading || tests.loading} />}
        {tab === "threats" && <Async state={top}>{({ m }) => <ThreatsPanel metrics={m} series={series.data} />}</Async>}
        {tab === "data" && <Async state={top}>{({ m }) => <DataProtectionPanel metrics={m} />}</Async>}
        {tab === "policy" && (
          <section className="sec" aria-label="Policy health">
            <h2>{SECTION_TITLES.policy}</h2>
            <p className="sub">Has anything been weakened, and what is the policy set to?</p>
            <Async state={controls}>{(c) => <ControlsPanel controls={c.controls} lastDiff={c.last_diff} />}</Async>
            <Async state={policy}>{(p) => (
              <>
                {p.summary && <PolicyGlance summary={p.summary} />}
                <PolicyPanel policy={p} />
              </>
            )}</Async>
            <Async state={signatures}>{(sg) => <KnownAttacks signatures={sg} />}</Async>
          </section>
        )}
        {tab === "cost" && <Async state={budgets}>{(b) => <BudgetsPanel budgets={b} cost={metrics.data?.cost ?? { local_usd: 0, external_usd: 0, compute_s: 0 }} />}</Async>}
        {tab === "speed" && <Async state={metrics}>{(m) => <SpeedPanel latency={m.latency} series={series.data} throughput={m.throughput_per_min} />}</Async>}
        {tab === "proof" && (
          <>
            <Async state={tests}>{(t) => <TestsPanel tests={t} />}</Async>
            <Async state={owasp}>{(o) => <OwaspPanel owasp={o} />}</Async>
          </>
        )}
      </div>
    </section>
  );
}
