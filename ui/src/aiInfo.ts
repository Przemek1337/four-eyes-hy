import type { AiInfo } from "./api/types";

/** The AI assessment of the deciding rule only: a deterministic decision must not show an unrelated AI model. */
export function pickAi(ai: Record<string, AiInfo> | null | undefined, rule?: string | null): AiInfo | null {
  if (!ai || !rule) return null;
  return ai[rule] ?? null;
}

const num = (n: number | null | undefined): string => (typeof n === "number" && Number.isFinite(n) ? n.toFixed(2) : "–");

export function aiSummary(a: AiInfo): string {
  const rule = a.rule ? ` · ${a.rule}` : "";
  const unsure = a.uncertain ? " · not confident" : "";
  return `${a.model}${rule} · p ${num(a.probability)} · confidence ${num(a.confidence)}${unsure}`;
}
