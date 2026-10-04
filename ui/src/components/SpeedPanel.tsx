import type { Latency, Metrics, TimeseriesT } from "../api/types";
import { BarList } from "../charts/BarList";
import { LineChart } from "../charts/LineChart";
import { fmtCount } from "../charts/scale";
import { fmtMs } from "../format";

const ms = (v: number): string => (v < 10 ? `${v.toFixed(1)} ms` : `${Math.round(v)} ms`);

/** Does it slow developers down? Load and gateway p95 as two charts (never one chart with two axes), the layer's cost next to the model's. */
export function SpeedPanel({ latency, series, throughput }: { latency: Latency; series: TimeseriesT | null; throughput?: Metrics["throughput_per_min"] }) {
  const pts = series?.points ?? [];
  const gw = latency.gateway, up = latency.upstream;
  const slowest = Object.entries(latency.controls).sort((a, b) => b[1].p95 - a[1].p95).slice(0, 3);
  const none = gw.count === 0;
  return (
    <section className="sec" aria-label="Gateway overhead">
      <h2>Speed</h2>
      <p className="sub">
        Does it slow developers down?{throughput != null ? ` Throughput now: ${fmtCount(Math.round(throughput))} requests a minute.` : ""}
      </p>
      <div className="two-charts even">
        <LineChart title="Requests per hour" sub="Load on the gateway over the last 24 hours."
                   seriesLabel="Requests" points={pts.map((p) => ({ t: p.ts, v: p.requests }))} />
        <LineChart title="Gateway p95 per hour" sub="How long the gateway itself takes at the slow end."
                   seriesLabel="Gateway p95" format={ms}
                   points={pts.filter((p) => p.gateway_p95_ms != null).map((p) => ({ t: p.ts, v: p.gateway_p95_ms as number }))}
                   emptyText="No latency recorded in this window yet." />
      </div>
      <div className="two-charts even lower">
        <BarList
          title="Gateway overhead vs model time"
          sub="The layer's cost next to the model's, in milliseconds. A mock or fast model makes the layer look large; compare the absolute times."
          valueLabel=""
          format={ms}
          sorted={false}
          highlight={["gw95"]}
          items={[
            { key: "gw50", label: "Gateway, median", value: gw.p50 },
            { key: "gw95", label: "Gateway, p95", value: gw.p95 },
            { key: "up50", label: "Model or tool, median", sub: "not our time", value: up.p50 },
            { key: "up95", label: "Model or tool, p95", sub: "not our time", value: up.p95 },
          ]}
          emptyText="No traffic yet."
        />
        <div>
          <h3 className="mini">Time per kind of check</h3>
          <dl className="facts2">
            <div><dt>Rule checks p50 / p95</dt><dd>{none ? "–" : `${fmtMs(latency.layers.det.p50)} / ${fmtMs(latency.layers.det.p95)}`}</dd></div>
            <div><dt>AI checks p50 / p95</dt><dd>{none ? "–" : `${fmtMs(latency.layers.ai.p50)} / ${fmtMs(latency.layers.ai.p95)}`}</dd></div>
            <div><dt>Gateway total p50 / p95</dt><dd>{none ? "–" : `${fmtMs(gw.p50)} / ${fmtMs(gw.p95)}`}</dd></div>
          </dl>
          <h3 className="mini">Slowest controls (p95)</h3>
          {slowest.length === 0 ? <p className="state">No control timings yet.</p> : (
            <ol className="slow">{slowest.map(([id, st]) => <li key={id}><code>{id}</code><span>{fmtMs(st.p95)}</span></li>)}</ol>
          )}
        </div>
      </div>
    </section>
  );
}
