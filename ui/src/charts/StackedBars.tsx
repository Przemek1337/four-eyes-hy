import type { ReactNode } from "react";
import { ChartFrame } from "./ChartFrame";
import { fmtCount } from "./scale";

export interface StackRow { key: string; label: string; a: number; b: number }

/** One horizontal bar per row, split in two parts with a 2 px gap. Two series, so a legend is always shown. */
export function StackedBars({ title, sub, aLabel, bLabel, rows, note, emptyText = "No traffic yet." }: {
  title: string; sub?: string; aLabel: string; bLabel: string; rows: StackRow[];
  note?: (row: StackRow) => ReactNode; emptyText?: string;
}) {
  const max = Math.max(1, ...rows.map((r) => r.a + r.b));
  const table = (
    <table className="chart-table">
      <caption>{title}</caption>
      <thead><tr><th>Data class</th><th>{aLabel}</th><th>{bLabel}</th></tr></thead>
      <tbody>{rows.map((r) => <tr key={r.key}><td>{r.label}</td><td>{fmtCount(r.a)}</td><td>{fmtCount(r.b)}</td></tr>)}</tbody>
    </table>
  );
  return (
    <ChartFrame title={title} sub={sub} table={table}>
      <ul className="legend2" aria-label="Legend">
        <li><i className="sw a" aria-hidden="true" />{aLabel}</li>
        <li><i className="sw b" aria-hidden="true" />{bLabel}</li>
      </ul>
      {rows.every((r) => r.a + r.b === 0) ? <p className="state">{emptyText}</p> : (
        <ul className="stack">
          {rows.map((r) => (
            <li key={r.key} tabIndex={0} aria-label={`${r.label}: ${fmtCount(r.a)} ${aLabel}, ${fmtCount(r.b)} ${bLabel}`}>
              <span className="st-name">{r.label}</span>
              <span className="st-bar" aria-hidden="true">
                {r.a > 0 && <i className="a" style={{ width: `${(r.a / max) * 100}%` }} />}
                {r.b > 0 && <i className="b" style={{ width: `${(r.b / max) * 100}%` }} />}
              </span>
              <span className="st-val"><b>{fmtCount(r.a + r.b)}</b>{note?.(r)}</span>
            </li>
          ))}
        </ul>
      )}
    </ChartFrame>
  );
}
