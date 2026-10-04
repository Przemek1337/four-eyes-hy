import type { ApprovalT, AuditEvent, JudgeInfo } from "../api/types";
import { Badge } from "./Badge";

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
  // The engine writes the detector score inside the alert or the verdict detail, and OWASP tags on the alert as well as on the event.
  const alertScore = (event.alerts ?? []).map((a) => a.score).find((x): x is number => typeof x === "number");
  const detailScore = typeof event.detail?.score === "number" ? (event.detail.score as number) : undefined;
  const score = event.injection_score ?? detailScore ?? alertScore;
  const owasp = [...new Set([...(event.owasp ?? []), ...(event.alerts ?? []).flatMap((a) => (Array.isArray(a.owasp) ? (a.owasp as string[]) : []))])];
  return (
    <section className="why" role="region" aria-label="Why this decision">
      <dl className="facts">
        <dt>Rule</dt>
        <dd>
          <code>{event.rule}</code>{event.code ? <> · <code>{event.code}</code></> : null}
          {event.policy_version ? <span className="muted"> · policy {event.policy_version}</span> : null}
        </dd>
        <dt>Layer</dt><dd>{event.layer === "ai" ? "AI (semantic)" : "Deterministic"}</dd>
        {event.reason && <><dt>Reason</dt><dd>{event.reason}</dd></>}
        {owasp.length > 0 && (
          <><dt>OWASP</dt><dd className="row">{owasp.map((t) => <Badge key={t}>{t}</Badge>)}</dd></>
        )}
        {event.signature_id && (
          <><dt>Signature</dt><dd><code>{event.signature_id}</code>{reference ? <div className="muted">{reference}</div> : null}</dd></>
        )}
        {typeof score === "number" && <><dt>Detector score</dt><dd>{score.toFixed(2)}</dd></>}
        {needsJudge && (
          <><dt>AI judge</dt><dd>{judge ? `${judge.consistent ? "consistent" : "inconsistent"} with the task (${judge.score.toFixed(2)}): ${judge.reason}` : "not run"}</dd></>
        )}
      </dl>
      {evidence && <pre className="evidence">{evidence}</pre>}
    </section>
  );
}
