import type { Metrics, TimeseriesT } from "../api/types";
import { BarList } from "../charts/BarList";
import { LineChart } from "../charts/LineChart";

/** Is the layer doing its job? How many requests were stopped, when, and by which rule. */
export function ThreatsPanel({ metrics, series }: { metrics: Metrics; series: TimeseriesT | null }) {
  const blockers = (metrics.top_blockers ?? []).slice(0, 5);
  return (
    <section className="sec" aria-label="Threats stopped">
      <h2>Threats stopped</h2>
      <p className="sub">Are attacks reaching the agents, and what is catching them?</p>
      <div className="two-charts">
        <LineChart
          title="Blocked per hour"
          sub="Requests FourEyes stopped, over the last 24 hours."
          seriesLabel="Blocked"
          points={(series?.points ?? []).map((p) => ({ t: p.ts, v: p.blocked }))}
        />
        <BarList
          title="What stopped them"
          sub="Rules that blocked the most requests, with their OWASP category."
          valueLabel="blocked"
          items={blockers.map((b) => ({ key: b.rule, label: b.rule, sub: b.owasp.join(", "), value: b.blocked }))}
          emptyText="Nothing has been blocked yet."
        />
      </div>
    </section>
  );
}
