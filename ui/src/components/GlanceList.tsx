import { SECTION_TITLES, type SectionId, type Summary } from "../managementSummary";

const ORDER: SectionId[] = ["threats", "data", "policy", "cost", "speed", "proof"];

/** One sentence per section. A lime dot means it needs a person; clicking a row opens that section. */
export function GlanceList({ summaries, onOpen, loading }: {
  summaries: Record<SectionId, Summary | null>;
  onOpen: (id: SectionId) => void;
  loading?: boolean;
}) {
  return (
    <ul className="glance-list" aria-label="Sections at a glance">
      {ORDER.map((id) => {
        const s = summaries[id];
        return (
          <li key={id}>
            <button onClick={() => onOpen(id)}>
              <span className={s?.attention ? "gl-mark attn" : "gl-mark"} aria-hidden="true" />
              <span className="gl-text">
                <b>{SECTION_TITLES[id]}{s?.attention && <em className="gl-flag">Needs attention</em>}</b>
                <span>{s ? s.text : loading ? "Loading…" : "Not available right now."}</span>
              </span>
              <span className="gl-open" aria-hidden="true">Open</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
