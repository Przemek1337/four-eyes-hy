import type { Tone } from "./components/Badge";

export const fmtMs = (ms: number | null | undefined): string => {
  if (ms == null || Number.isNaN(ms)) return "–";
  if (ms < 1) return `${ms.toFixed(2)} ms`;
  return ms < 100 ? `${ms.toFixed(1)} ms` : `${Math.round(ms)} ms`;
};
export const fmtUsd = (n: number): string => `$${n.toFixed(n < 1 ? 4 : 2)}`;
export const fmtPct = (p: number | null | undefined): string => (p == null || Number.isNaN(p) ? "no limit" : `${Math.round(p)}%`);
export const fmtTime = (value: string | number | null | undefined): string => {
  if (value == null) return "–";
  const d = typeof value === "number" ? new Date(value * 1000) : new Date(value);
  return Number.isNaN(d.getTime()) ? "–" : d.toLocaleTimeString([], { hour12: false });
};
export const shortHash = (h: string): string => (h.length > 14 ? `${h.slice(0, 8)}…${h.slice(-4)}` : h);

/* Tones are shapes, not hues (design spec section 3):
   blue = grey outline, orange = dashed outline, red = lime fill with a cross, yellow = lime outline,
   green = white outline, gray = plain. */
export const decisionTone = (d?: string | null): Tone =>
  d === "BLOCK" ? "red" : d === "APPROVAL" ? "yellow" : d === "REDACT" ? "orange" : d === "ALLOW" ? "blue" : "gray";
export const classTone = (c?: string | null): Tone =>
  c === "bank_secret" || c === "personal_data" ? "green" : "gray";
export const statusTone = (s?: string | null): Tone =>
  s === "high_risk" ? "green" : s === "untrusted" ? "orange" : "blue";
