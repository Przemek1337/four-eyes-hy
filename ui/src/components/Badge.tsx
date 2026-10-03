import type { ReactNode } from "react";
import { decisionTone } from "../format";

export type Tone = "blue" | "orange" | "red" | "green" | "yellow" | "gray";

export function Badge({ tone = "gray", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {children}
    </span>
  );
}

export function DecisionPill({ decision }: { decision?: string | null }) {
  return <Badge tone={decisionTone(decision)}>{decision ?? "–"}</Badge>;
}

const STATUS_LABEL = { clean: "Clean", untrusted: "Untrusted", high_risk: "High risk" } as const;

/** Session status as a mark plus a word: hollow ring, dashed ring, or filled dot. Never colour alone. */
export function StatusMark({ status }: { status: keyof typeof STATUS_LABEL }) {
  const cls = status === "high_risk" ? "st untrusted risk" : status === "untrusted" ? "st untrusted" : "st";
  return (
    <span className={cls}>
      <i aria-hidden="true" />
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}
