import type { AiInfo } from "./api/types";

/** The AI assessment behind a decision: the deciding control's own, else the first one recorded. */
export function pickAi(ai: Record<string, AiInfo> | null | undefined, rule?: string | null): AiInfo | null {
  if (!ai) return null;
  return (rule ? ai[rule] : undefined) ?? Object.values(ai)[0] ?? null;
}

export function aiSummary(a: AiInfo): string {
  const rule = a.rule ? ` · ${a.rule}` : "";
  const unsure = a.uncertain ? " · not confident" : "";
  return `${a.model}${rule} · p ${a.probability.toFixed(2)} · confidence ${a.confidence.toFixed(2)}${unsure}`;
}
