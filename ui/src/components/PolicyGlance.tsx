import type { LabelValue, PolicyT } from "../api/types";

function Column({ title, items }: { title: string; items: LabelValue[] }) {
  return (
    <div>
      <h4>{title}</h4>
      <ul>{items.map((i) => <li key={i.label}><span>{i.label}</span><b>{i.value}</b></li>)}</ul>
    </div>
  );
}

/** The thresholds, models and budgets the policy file sets right now, in plain words. */
export function PolicyGlance({ summary }: { summary: NonNullable<PolicyT["summary"]> }) {
  return (
    <section className="subsec" aria-label="Policy at a glance">
      <h3>Policy at a glance</h3>
      <p className="sub">One file sets all of this and reloads without a restart.</p>
      <div className="glance">
        <Column title="Block or redact" items={summary.block_or_redact} />
        <Column title="Allowed models" items={summary.models} />
        <Column title="Budget rules" items={summary.budgets} />
      </div>
    </section>
  );
}
