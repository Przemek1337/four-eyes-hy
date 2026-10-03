import { ChartFrame } from "./ChartFrame";
import { fmtCount } from "./scale";

export interface BarItem { key: string; label: string; sub?: string; value: number }

/** Ranked horizontal bars for a nominal list: one colour, the leader in the accent, the value at the tip. */
export function BarList({ title, sub, valueLabel, items, format = fmtCount, sorted: rank = true, highlight, emptyText = "Nothing to rank yet." }: {
  title: string; sub?: string; valueLabel: string; items: BarItem[]; format?: (v: number) => string;
  /** rank by value (default) or keep the given order */
  sorted?: boolean;
  /** keys drawn in the accent; defaults to the leader when ranked */
  highlight?: string[]; emptyText?: string;
}) {
  const sorted = rank ? [...items].sort((a, b) => b.value - a.value) : [...items];
  const lead = new Set(highlight ?? (rank && sorted[0] ? [sorted[0].key] : []));
  const max = Math.max(1, ...sorted.map((i) => i.value));
  const table = (
    <table className="chart-table">
      <caption>{title}</caption>
      <thead><tr><th>Name</th><th>{valueLabel}</th></tr></thead>
      <tbody>{sorted.map((i) => <tr key={i.key}><td>{i.label}{i.sub ? ` (${i.sub})` : ""}</td><td>{format(i.value)}</td></tr>)}</tbody>
    </table>
  );
  return (
    <ChartFrame title={title} sub={sub} table={table}>
      {sorted.length === 0 ? <p className="state">{emptyText}</p> : (
        <ul className="barlist">
          {sorted.map((it) => (
            <li key={it.key} tabIndex={0} aria-label={`${it.label}: ${format(it.value)} ${valueLabel}`.trim()}>
              <span className="bl-name"><span>{it.label}</span>{it.sub && <small>{it.sub}</small>}</span>
              <span className="bl-track" aria-hidden="true">
                <i className={lead.has(it.key) ? "lead" : undefined} style={{ width: `${Math.max(2, (it.value / max) * 100)}%` }} />
              </span>
              <b className="bl-val">{format(it.value)}</b>
            </li>
          ))}
        </ul>
      )}
    </ChartFrame>
  );
}
