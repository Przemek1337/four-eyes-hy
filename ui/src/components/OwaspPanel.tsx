import type { OwaspT } from "../api/types";

const STATUS = { enforced: "", monitor_only: "mon", uncovered: "unc" } as const;
const NOTE = { enforced: "", monitor_only: "monitor only", uncovered: "uncovered" } as const;

/** One tile per OWASP category, with the edition year. Filled dot = enforced, half = monitor only, dashed = uncovered. */
export function OwaspPanel({ owasp }: { owasp: OwaspT }) {
  const count = (s: keyof typeof STATUS) => owasp.categories.filter((c) => c.status === s).length;
  const parts = [`${count("enforced")} enforced`, `${count("monitor_only")} monitor only`];
  if (count("uncovered") > 0) parts.push(`${count("uncovered")} uncovered`);
  return (
    <section className="sec" aria-label="OWASP coverage">
      <h2>OWASP LLM Top 10 ({owasp.edition}): {owasp.tested} categories tested</h2>
      <p className="sub">{parts.join(", ")}. Coverage follows the controls active right now.</p>
      <div className="owasp">
        {owasp.categories.map((c) => (
          <div key={c.id} className="ot" role="group" aria-label={c.id}>
            <div className="id">{c.id}<span className={`cov ${STATUS[c.status]}`.trim()} aria-hidden="true" /></div>
            <b>{c.name}</b>
            <span className="n">
              {c.status === "enforced"
                ? `${c.blocks} blocked`
                : [NOTE[c.status], c.note].filter(Boolean).join(" · ")}
            </span>
          </div>
        ))}
      </div>
      <div className="legend">
        <span><i className="cov" />Enforced</span><span><i className="cov mon" />Monitor only</span><span><i className="cov unc" />Uncovered</span>
      </div>
    </section>
  );
}
