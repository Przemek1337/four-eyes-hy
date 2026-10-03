import type { ApprovalT, AuditEvent, JudgeInfo } from "../api/types";
import { Badge, DecisionPill } from "./Badge";

/** Why a step was allowed, stopped or held. Rendered inside the selected timeline step. */
export function WhyBlocked({ event, approval }: { event: AuditEvent | null; approval?: ApprovalT | null }) {
  if (!event) {
    return <p className="state">Select a step to see the rule behind it.</p>;
  }
  const judge: JudgeInfo | null = approval?.judge ?? ((event.detail?.judge as JudgeInfo | undefined) ?? null);
  const needsJudge = event.layer === "ai" || event.decision === "APPROVAL";
  const evidence = event.evidence
    ?? (event.detail?.evidence as string | undefined)
    ?? (event.alerts ?? []).map((a) => a.fragment).find((f): f is string => typeof f === "string");
  const reference = event.reference ?? (event.detail?.reference as string | undefined);
  return (
    <section className="why" role="region" aria-label="Why this decision">
      <dl className="facts">
        <dt>Decision</dt><dd><DecisionPill decision={event.decision} /></dd>
        <dt>Rule</dt>
        <dd>
          <code>{event.rule}</code>{event.code ? <> · <code>{event.code}</code></> : null}
          {event.policy_version ? <span className="muted"> · policy {event.policy_version}</span> : null}
        </dd>
        <dt>Layer</dt><dd>{event.layer === "ai" ? "AI (semantic)" : "Deterministic"}</dd>
        <dt>Reason</dt><dd>{event.reason || "–"}</dd>
        {(event.owasp ?? []).length > 0 && (
          <><dt>OWASP</dt><dd className="row">{event.owasp!.map((t) => <Badge key={t}>{t}</Badge>)}</dd></>
        )}
        {event.signature_id && (
          <><dt>Signature</dt><dd><code>{event.signature_id}</code>{reference ? <div className="muted">{reference}</div> : null}</dd></>
        )}
        {typeof event.injection_score === "number" && <><dt>Detector score</dt><dd>{event.injection_score.toFixed(2)}</dd></>}
        {needsJudge && (
          <><dt>AI judge</dt><dd>{judge ? `${judge.consistent ? "consistent" : "inconsistent"} with the task (${judge.score.toFixed(2)}): ${judge.reason}` : "not run"}</dd></>
        )}
      </dl>
      {evidence && <pre className="evidence">{evidence}</pre>}
    </section>
  );
}
