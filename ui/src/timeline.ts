import type { AuditEvent, Decision, SessionDetailT } from "./api/types";
import type { Tone } from "./components/Badge";

export interface TimelineItem {
  key: string;
  kind: "step" | "note";
  n?: number;
  title: string;
  summary: string;
  tone: Tone;
  decision?: Decision;
  /** the session already carried an untrusted or high_risk label when this step ran */
  tainted: boolean;
  ts?: string;
  ms?: number;
  route?: string;
  event: AuditEvent;
}

const TAINTED = new Set(["untrusted", "high_risk"]);

export function alertText(a: { kind: string } & Record<string, unknown>): string {
  const score = typeof a.score === "number" ? a.score.toFixed(2) : undefined;
  switch (a.kind) {
    case "document.injection": return `Injection detector flagged the document${score ? ` (score ${score})` : ""}`;
    case "document.signature": return `Signature ${String(a.signature)} flagged the document`;
    case "prompt.suspicious": return `Suspicious prompt${score ? ` (score ${score})` : ""}`;
    case "budget.soft": return `Budget at ${String(a.pct)}%`;
    case "pii.detected": return "Personal data detected";
    case "dlp.detected": return "DLP detection (monitor mode)";
    case "judge.inconsistent": return "The AI judge found the action inconsistent with the task";
    case "output.canary": return "A canary from the system prompt appeared in the output";
    case "output.unsafe": return "Unsafe content found in the output";
    default: return a.kind;
  }
}

export function summaryFor(ev: AuditEvent): string {
  const parts: string[] = [];
  if (ev.decision === "BLOCK" || ev.decision === "APPROVAL") {
    parts.push(`${ev.decision === "BLOCK" ? "Blocked" : "Held for approval"} by ${ev.rule}${ev.code ? ` (${ev.code})` : ""}`);
  }
  if (ev.kind === "model" && ev.route) {
    parts.push(`Route: ${ev.data_class} → ${ev.route.chosen} (${ev.route.model}, router ${ev.route.router})`);
  }
  if (ev.route?.rerouted_from) parts.push(`rerouted from ${ev.route.rerouted_from}`);
  if (ev.anonymization === "not_applied") parts.push("external provider: anonymization not applied");
  if (ev.redaction && ev.redaction !== "on") parts.push(`log redaction ${ev.redaction}`);
  for (const a of ev.alerts ?? []) parts.push(alertText(a));
  if (ev.decision === "REDACT") parts.push(ev.reason || "redacted");
  return parts.join(" · ") || "Allowed";
}

export function buildTimeline(events: AuditEvent[]): TimelineItem[] {
  let n = 0;
  return events.flatMap((ev, i): TimelineItem[] => {
    if (ev.event === "decision") {
      n += 1;
      const stopped = ev.decision === "BLOCK" || ev.decision === "APPROVAL";
      const tainted = (ev.labels ?? []).some((l) => TAINTED.has(l));
      const tone: Tone = stopped ? "red" : tainted ? "orange" : "blue";
      return [{
        key: ev.decision_id ?? `d${i}`, kind: "step", n, title: ev.kind === "tool" ? String(ev.resource) : "Model call",
        summary: summaryFor(ev), tone, decision: ev.decision, tainted, ts: ev.ts, ms: ev.latency_ms, route: ev.route?.chosen, event: ev,
      }];
    }
    if (ev.event === "class.raised") {
      return [{ key: `c${i}`, kind: "note", title: "Data class raised", summary: `${ev.from} → ${ev.to} (${ev.reason ?? ev.source ?? "source"})`, tone: "orange", tainted: false, event: ev }];
    }
    if (ev.event === "label.added") {
      return [{ key: `l${i}`, kind: "note", title: String(ev.label), summary: ev.reason ?? "label added", tone: ev.label === "high_risk" ? "red" : "orange", tainted: false, event: ev }];
    }
    return [];
  });
}

/** Step number at which the session first carried an untrusted or high_risk label, or null. */
export function taintedFrom(items: TimelineItem[]): number | null {
  return items.find((i) => i.kind === "step" && i.tainted)?.n ?? null;
}

/** Plain-language title: what the agent tried and what FourEyes did about it. */
export function headlineFor(session: SessionDetailT["session"], items: TimelineItem[]): string {
  const steps = items.filter((i) => i.kind === "step");
  const what = (i: TimelineItem) => (i.title === "Model call" ? "a model call" : i.title);
  const blocked = [...steps].reverse().find((i) => i.decision === "BLOCK");
  if (blocked) return `${session.agent} tried ${what(blocked)} and FourEyes stopped it`;
  const held = [...steps].reverse().find((i) => i.decision === "APPROVAL");
  if (held) return `${session.agent} tried ${what(held)}. It is waiting for a human`;
  if (steps.length === 0) return `${session.agent} has not done anything yet`;
  return `${session.agent} ran ${steps.length} step${steps.length === 1 ? "" : "s"} and nothing was stopped`;
}
