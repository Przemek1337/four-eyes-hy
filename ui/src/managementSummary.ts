import type { BudgetsT, ControlRow, Metrics, OwaspT, PolicyT, TestsT, TimeseriesT } from "./api/types";
import { fmtClock, fmtCount } from "./charts/scale";
import { fmtMs, fmtUsd } from "./format";

export type TabId = "overview" | "threats" | "data" | "policy" | "cost" | "speed" | "proof";
export type SectionId = Exclude<TabId, "overview">;
export interface Summary { text: string; attention: boolean }

export const SECTION_TITLES: Record<SectionId, string> = {
  threats: "Threats stopped",
  data: "Data protection",
  policy: "Policy health",
  cost: "Cost",
  speed: "Speed",
  proof: "Proof it works",
};

export interface SummaryInput {
  metrics?: Metrics | null;
  series?: TimeseriesT | null;
  controls?: ControlRow[] | null;
  policy?: PolicyT | null;
  budgets?: BudgetsT | null;
  tests?: TestsT | null;
  owasp?: OwaspT | null;
}

/** One plain sentence per section, and whether it needs a person's attention. null while there is nothing to say. */
export function buildSummaries(d: SummaryInput): Record<SectionId, Summary | null> {
  const m = d.metrics;

  let threats: Summary | null = null;
  if (m) {
    const share = m.requests > 0 ? Math.round((m.by_decision.BLOCK / m.requests) * 100) : 0;
    const parts = [`${fmtCount(m.by_decision.BLOCK)} blocked (${share}% of requests).`];
    const peak = (d.series?.points ?? []).reduce<{ ts: number; blocked: number } | null>((a, p) => (!a || p.blocked > a.blocked ? p : a), null);
    if (peak && peak.blocked > 0) parts.push(`Busiest hour: ${peak.blocked} at ${fmtClock(peak.ts)}.`);
    if (m.top_blockers?.[0]) parts.push(`Most stopped by ${m.top_blockers[0].rule}.`);
    threats = { text: parts.join(" "), attention: false };
  }

  let data: Summary | null = null;
  if (m) {
    data = m.private_to_external > 0
      ? { text: `${fmtCount(m.private_to_external)} private request(s) reached an external model. This must be 0.`, attention: true }
      : { text: `No private data reached an external model.${m.redacted_fields != null ? ` ${fmtCount(m.redacted_fields)} fields were removed on the way.` : ""}`, attention: false };
  }

  let policy: Summary | null = null;
  if (d.controls) {
    const removed = d.controls.filter((c) => c.status === "REMOVED").map((c) => c.id);
    const active = d.controls.filter((c) => c.status !== "REMOVED").length;
    if (removed.length > 0) policy = { text: `${removed.join(", ")} removed. ${active} of ${d.controls.length} controls active.`, attention: true };
    else if (d.policy?.error) policy = { text: "The last policy change was rejected. The previous policy is still running.", attention: true };
    else if (d.policy?.feed.error) policy = { text: "The signature feed has an error.", attention: true };
    else policy = { text: `${active} of ${d.controls.length} controls active${d.policy ? `, ${d.policy.profile} profile` : ""}.`, attention: false };
  }

  let cost: Summary | null = null;
  if (d.budgets) {
    const rows = [...d.budgets.agents.map((a) => ({ name: a.agent, level: a.level })), ...d.budgets.teams.map((t) => ({ name: t.team, level: t.level }))];
    const over = rows.filter((r) => r.level === "over").map((r) => `${r.name} at its limit`);
    const warn = rows.filter((r) => r.level === "warn").map((r) => `${r.name} near its limit`);
    const spent = m ? ` Spent ${fmtUsd(m.cost.external_usd + m.cost.local_usd)}.` : "";
    cost = over.length + warn.length > 0
      ? { text: `${[...over, ...warn].join(", ")}.${spent}`, attention: true }
      : { text: `All budgets are within their limits.${spent}`, attention: false };
  }

  let speed: Summary | null = null;
  if (m) {
    const gw = m.latency.gateway, up = m.latency.upstream;
    speed = gw.count === 0
      ? { text: "No traffic yet.", attention: false }
      : { text: `The gateway adds ${fmtMs(gw.p50)} at the median and ${fmtMs(gw.p95)} at p95. The model or tool took ${fmtMs(up.p95)} at p95.`, attention: false };
  }

  let proof: Summary | null = null;
  if (d.tests) {
    const t = d.tests;
    const enforced = d.owasp ? ` ${d.owasp.categories.filter((c) => c.status === "enforced").length} of ${d.owasp.categories.length} OWASP categories enforced.` : "";
    proof = t.ran_at == null
      ? { text: "No test report yet.", attention: true }
      : { text: `${t.passed} of ${t.passed + t.failed} tests pass. Missed attacks in tests ${t.missed_attacks}, false blocks ${t.false_blocks}.${enforced}`, attention: t.failed > 0 || t.missed_attacks > 0 || t.false_blocks > 0 };
  }
  return { threats, data, policy, cost, speed, proof };
}
