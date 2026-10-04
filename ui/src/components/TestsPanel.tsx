import type { CorpusT, TestsT } from "../api/types";
import { fmtTime } from "../format";

const pct = (r: number | null) => (r == null ? "n/a" : `${(r * 100).toFixed(1)}%`);

/** Results on the synthetic corpus: hundreds of generated attacks and legitimate cases, not hand-picked examples. */
function CorpusResults({ corpus }: { corpus: CorpusT }) {
  const owasp = Object.entries(corpus.by_owasp).sort(([a], [b]) => a.localeCompare(b));
  const techniques = Object.entries(corpus.by_technique).sort(([a], [b]) => a.localeCompare(b));
  return (
    <div className="corpus" aria-label="Synthetic corpus">
      <h3>Synthetic attack corpus</h3>
      <p className="sub">Generated attacks and legitimate cases (fictitious clients, valid-by-checksum identifiers). Known gaps are measured and listed, not hidden.</p>
      <div className="kpis proof">
        <div className="kpi" role="group" aria-label="Attack detection">
          <b>{pct(corpus.detection_rate)}</b>
          <span>Attacks stopped</span>
          <small>{corpus.attacks_stopped} of {corpus.attacks} generated attacks</small>
        </div>
        <div className={corpus.false_blocks === 0 ? "kpi hold" : "kpi"} role="group" aria-label="Corpus false blocks">
          <b>{pct(corpus.false_block_rate)}</b>
          <span>False blocks</span>
          <small>{corpus.false_blocks} of {corpus.benign} legitimate cases</small>
        </div>
        <div className="kpi" role="group" aria-label="Known gaps">
          <b>{corpus.known_gap_count}</b>
          <span>Known gaps</span>
          <small>attacks the layer does not stop yet</small>
        </div>
      </div>
      <details className="owasp-tests">
        <summary>Corpus results by OWASP category</summary>
        <table className="chart-table">
          <thead><tr><th>Category</th><th>Attacks stopped</th><th>Legitimate blocked</th></tr></thead>
          <tbody>
            {owasp.map(([id, r]) => (
              <tr key={id}><td>{id}</td><td>{r.attacks > 0 ? `${r.stopped} / ${r.attacks}` : "n/a"}</td><td className={r.false_blocks > 0 ? "bad" : undefined}>{r.benign > 0 ? `${r.false_blocks} / ${r.benign}` : "n/a"}</td></tr>
            ))}
          </tbody>
        </table>
      </details>
      <details className="owasp-tests">
        <summary>Corpus results by attack technique</summary>
        <table className="chart-table">
          <thead><tr><th>Technique</th><th>Stopped</th></tr></thead>
          <tbody>
            {techniques.map(([name, r]) => (
              <tr key={name}><td>{name}</td><td>{`${r.stopped} / ${r.attacks}`}</td></tr>
            ))}
          </tbody>
        </table>
      </details>
      {corpus.known_gaps.length > 0 && (
        <details className="owasp-tests">
          <summary>Known gaps ({corpus.known_gap_count})</summary>
          <table className="chart-table">
            <thead><tr><th>Category</th><th>Technique</th><th>Example</th></tr></thead>
            <tbody>
              {corpus.known_gaps.map((g, i) => (
                <tr key={i}><td>{g.owasp}</td><td>{g.technique}</td><td>{g.sample}</td></tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </div>
  );
}

/** Proof the guardrails work. Missed attacks and false blocks are the honest quality numbers: both should be zero. */
export function TestsPanel({ tests }: { tests: TestsT }) {
  const total = tests.passed + tests.failed;
  const owasp = Object.entries(tests.by_owasp).sort(([a], [b]) => a.localeCompare(b));
  if (tests.ran_at == null) {
    return (
      <section className="sec" aria-label="Test suite">
        <h2>Proof it works</h2>
        <p className="state">No test report yet.</p>
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
      {tests.corpus && tests.corpus.attacks > 0 && <CorpusResults corpus={tests.corpus} />}
    </section>
  );
}
