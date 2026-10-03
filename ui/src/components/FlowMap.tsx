import type { FlowT } from "../api/types";

const OUTCOME_TEXT = { passed: "passed", blocked: "blocked", held: "held for approval", unavailable: "unavailable for this session" } as const;

/** Read-only "where the data went": sources, the agent, and where data was allowed to go. */
export function FlowMap({ flow }: { flow: FlowT }) {
  return (
    <section className="flow" aria-label="Where the data went">
      <h2>Where the data went</h2>
      <div className="cols">
        <div className="col-flow">
          <h3>Sources</h3>
          {flow.sources.map((s) => (
            <div key={s.name} className={s.label === "untrusted" ? "node-card dashed" : "node-card"}>
              <b>{s.name}</b><span>{s.detail}</span><em>{s.label}</em>
            </div>
          ))}
        </div>
        <div className="arrow" aria-hidden="true">→</div>
        <div className="col-flow agent">
          <h3>Agent</h3>
          <div className="node-card big">
            <b>{flow.agent.name}</b><span>{flow.agent.model}</span>
            <div className="chips">{flow.agent.labels.map((l) => <em key={l}>{l}</em>)}</div>
            {flow.agent.labels_since_step != null && <span className="small">Labels added at step {flow.agent.labels_since_step}</span>}
          </div>
        </div>
        <div className="arrow" aria-hidden="true">→</div>
        <div className="col-flow">
          <h3>Destinations</h3>
          {flow.destinations.map((d) => (
            <div key={d.name} className={`node-card ${d.outcome}`}>
              <b>{d.name}</b><span>{d.detail}</span><em>{OUTCOME_TEXT[d.outcome]}</em>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
