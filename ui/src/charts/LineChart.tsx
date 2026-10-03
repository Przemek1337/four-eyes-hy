import { useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { ChartFrame } from "./ChartFrame";
import { fmtClock, fmtCount, niceMax } from "./scale";
import { useWidth } from "./useWidth";

export interface Point { t: number; v: number }

const H = 200;
const PAD = { l: 40, r: 56, t: 14, b: 28 };

/** One series over time: 2 px line, a 10% wash under it, hairline grid, the latest value labelled at the end.
 *  A crosshair snaps to the nearest point; arrow keys do the same. Every value is also in the table view. */
export function LineChart({ title, sub, seriesLabel, points, emptyText = "No data in this window yet." }: {
  title: string; sub?: string; seriesLabel: string; points: Point[]; emptyText?: string;
}) {
  const [wrap, width] = useWidth<HTMLDivElement>();
  const svg = useRef<SVGSVGElement>(null);
  const [active, setActive] = useState<number | null>(null);

  const table = (
    <table className="chart-table">
      <caption>{seriesLabel} over time</caption>
      <thead><tr><th>Time</th><th>{seriesLabel}</th></tr></thead>
      <tbody>{points.map((p) => <tr key={p.t}><td>{fmtClock(p.t)}</td><td>{fmtCount(p.v)}</td></tr>)}</tbody>
    </table>
  );

  if (points.length === 0) {
    return <ChartFrame title={title} sub={sub} table={table}><p className="state">{emptyText}</p></ChartFrame>;
  }

  const ts = points.map((p) => p.t);
  const t0 = Math.min(...ts), t1 = Math.max(...ts);
  const max = Math.max(...points.map((p) => p.v));
  const yMax = niceMax(max);
  const iw = Math.max(40, width - PAD.l - PAD.r), ih = H - PAD.t - PAD.b;
  const x = (t: number) => PAD.l + (t1 === t0 ? iw / 2 : ((t - t0) / (t1 - t0)) * iw);
  const y = (v: number) => PAD.t + ih - (v / yMax) * ih;
  const line = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.t).toFixed(1)} ${y(p.v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(t1).toFixed(1)} ${PAD.t + ih} L${x(t0).toFixed(1)} ${PAD.t + ih} Z`;
  const yTicks = yMax >= 4 ? [0, yMax / 2, yMax] : [0, yMax];
  const nTicks = Math.min(5, points.length);
  const xTicks = Array.from({ length: nTicks }, (_, i) => points[Math.round((i * (points.length - 1)) / Math.max(1, nTicks - 1))]);
  const last = points[points.length - 1];
  const total = points.reduce((s, p) => s + p.v, 0);
  const peak = points.reduce((a, p) => (p.v > a.v ? p : a), points[0]);

  const nearest = (clientX: number) => {
    const rect = svg.current?.getBoundingClientRect();
    const px = (clientX - (rect?.left ?? 0)) * (width / (rect?.width || width));
    let best = 0, d = Infinity;
    points.forEach((p, i) => { const dd = Math.abs(x(p.t) - px); if (dd < d) { d = dd; best = i; } });
    return best;
  };
  const onKey = (e: KeyboardEvent) => {
    const i = active ?? points.length - 1;
    if (e.key === "ArrowLeft") { e.preventDefault(); setActive(Math.max(0, i - 1)); }
    else if (e.key === "ArrowRight") { e.preventDefault(); setActive(Math.min(points.length - 1, i + 1)); }
    else if (e.key === "Home") { e.preventDefault(); setActive(0); }
    else if (e.key === "End") { e.preventDefault(); setActive(points.length - 1); }
    else if (e.key === "Escape") setActive(null);
  };
  const a = active != null ? points[active] : null;
  const tipLeft = a ? Math.min(Math.max(x(a.t), 70), width - 70) : 0;

  return (
    <ChartFrame title={title} sub={sub} table={table}>
      <div className="plot" ref={wrap}>
        <svg ref={svg} width={width} height={H} role="img"
             aria-label={`${seriesLabel}: ${fmtCount(total)} in total, peak ${fmtCount(peak.v)} at ${fmtClock(peak.t)}, latest ${fmtCount(last.v)}`}>
          {yTicks.map((tv) => (
            <g key={tv}>
              <line className="grid" x1={PAD.l} x2={width - PAD.r} y1={y(tv)} y2={y(tv)} />
              <text className="tick" x={PAD.l - 8} y={y(tv) + 4} textAnchor="end">{fmtCount(tv)}</text>
            </g>
          ))}
          {xTicks.map((p, i) => (
            <text key={`${p.t}-${i}`} className="tick" x={x(p.t)} y={H - 8} textAnchor={i === 0 ? "start" : i === xTicks.length - 1 ? "end" : "middle"}>{fmtClock(p.t)}</text>
          ))}
          <path d={area} className="area" />
          <path d={line} className="line" />
          <circle className="end-ring" cx={x(last.t)} cy={y(last.v)} r={6} />
          <circle className="end-dot" cx={x(last.t)} cy={y(last.v)} r={4} />
          <text className="end-label" x={x(last.t) + 12} y={y(last.v) + 4}>{fmtCount(last.v)}</text>
          {a && (
            <g>
              <line className="cross" x1={x(a.t)} x2={x(a.t)} y1={PAD.t} y2={PAD.t + ih} />
              <circle className="end-ring" cx={x(a.t)} cy={y(a.v)} r={6} />
              <circle className="end-dot" cx={x(a.t)} cy={y(a.v)} r={4} />
            </g>
          )}
          <rect className="hit" x={PAD.l} y={PAD.t} width={iw} height={ih} tabIndex={0} role="group"
                aria-label={`${seriesLabel} by time. Use the arrow keys to read each point.`}
                onPointerMove={(e: PointerEvent) => setActive(nearest(e.clientX))}
                onPointerLeave={() => setActive(null)}
                onFocus={() => setActive((i) => i ?? points.length - 1)}
                onBlur={() => setActive(null)}
                onKeyDown={onKey} />
        </svg>
        {a && (
          <div className="tip" role="status" style={{ left: tipLeft, top: Math.max(0, y(a.v) - 56) }}>
            <b>{fmtCount(a.v)}</b>
            <span><i className="key" aria-hidden="true" />{seriesLabel}</span>
            <small>{fmtClock(a.t)}</small>
          </div>
        )}
      </div>
    </ChartFrame>
  );
}
