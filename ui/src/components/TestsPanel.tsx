import type { TestsT } from "../api/types";
import { fmtTime } from "../format";

/** Proof the guardrails work. Missed attacks and false blocks are the honest quality numbers: both should be zero. */
export function TestsPanel({ tests }: { tests: TestsT }) {
  const total = tests.passed + tests.failed;
  const owasp = Object.entries(tests.by_owasp).sort(([a], [b]) => a.localeCompare(b));
  if (tests.ran_at == null) {
    return (
      <section className="sec" aria-label="Test suite">
        <h2>Proof it works</h2>
        <p className="state">No test report yet. Run <code>make test</code> to produce one.</p>
      </section>
    );
  }
  return (
    <section className="sec" aria-label="Test suite">
      <h2>Proof it works</h2>
      <p className="sub">Does the layer allow what it should and stop what it should? Last run {fmtTime(tests.ran_at)}{tests.policy_version ? `, policy ${tests.policy_version}` : ""}. Run it yourself with <code>make test</code>.</p>
      <div className="kpis proof">
        <div className="kpi" role="group" aria-label="Tests passed">
          <b className={tests.failed > 0 ? "bad" : undefined}>{tests.passed} / {total}</b>
          <span>Tests passed</span>
          <small>{tests.positive.passed} allowed cases · {tests.negative.passed} stopped cases</small>
        </div>
        <div className={tests.missed_attacks === 0 ? "kpi hold" : "kpi"} role="group" aria-label="Missed attacks">
          <b>{tests.missed_attacks}{tests.missed_attacks > 0 && <span className="badge badge-red kpi-breach">Gap</span>}</b>
          <span>Missed attacks</span>
          <small>attacks the layer let through</small>
        </div>
        <div className={tests.false_blocks === 0 ? "kpi hold" : "kpi"} role="group" aria-label="False blocks">
          <b>{tests.false_blocks}{tests.false_blocks > 0 && <span className="badge badge-red kpi-breach">Gap</span>}</b>
          <span>False blocks</span>
          <small>legitimate requests it stopped</small>
        </div>
      </div>
      {owasp.length > 0 && (
        <details className="owasp-tests">
          <summary>Results by OWASP category</summary>
          <table className="chart-table">
            <thead><tr><th>Category</th><th>Passed</th></tr></thead>
            <tbody>
              {owasp.map(([id, r]) => (
                <tr key={id}><td>{id}</td><td className={r.failed > 0 ? "bad" : undefined}>{`${r.passed} / ${r.passed + r.failed}`}</td></tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </section>
  );
}
