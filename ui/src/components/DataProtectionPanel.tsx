import type { Metrics } from "../api/types";
import { StackedBars } from "../charts/StackedBars";
import { fmtCount } from "../charts/scale";

const ORDER = ["public", "personal_data", "bank_secret"];
const PRIVATE = new Set(["personal_data", "bank_secret"]);

/** Is private data staying inside the bank? Where each data class went, and what was removed on the way. */
export function DataProtectionPanel({ metrics }: { metrics: Metrics }) {
  const rows = [...(metrics.routing ?? [])]
    .sort((x, y) => ORDER.indexOf(x.data_class) - ORDER.indexOf(y.data_class))
    .map((r) => ({ key: r.data_class, label: r.data_class, a: r.local, b: r.external }));
  return (
    <section className="sec" aria-label="Data protection">
      <h2>Data protection</h2>
      <p className="sub">Is private data staying inside the bank?</p>
      <StackedBars
        title="Where each data class went"
        sub="Requests per data class, by the model that answered. Private data must stay on the local model."
        aLabel="Local model"
        bLabel="External model"
        rows={rows}
        note={(r) => PRIVATE.has(r.key)
          ? r.b === 0 ? <span className="ok-note">0 to external</span> : <span className="badge badge-red">{`${fmtCount(r.b)} to external`}</span>
          : null}
      />
      {metrics.redacted_fields != null && (
        <p className="redacted-line"><b>{fmtCount(metrics.redacted_fields)}</b> fields removed before they left the gateway.</p>
      )}
    </section>
  );
}
