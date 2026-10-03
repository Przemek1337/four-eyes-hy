import { useState, type ReactNode } from "react";

/** Title, one line that says how to read it, and a switch to the table that carries the same numbers. */
export function ChartFrame({ title, sub, table, children }: { title: string; sub?: string; table: ReactNode; children: ReactNode }) {
  const [asTable, setAsTable] = useState(false);
  return (
    <figure className="chart" aria-label={title}>
      <figcaption>
        <div>
          <h3>{title}</h3>
          {sub && <p>{sub}</p>}
        </div>
        <button className="linkbtn" aria-pressed={asTable} onClick={() => setAsTable((v) => !v)}>
          {asTable ? "View as chart" : "View as table"}
        </button>
      </figcaption>
      {asTable ? table : children}
    </figure>
  );
}
