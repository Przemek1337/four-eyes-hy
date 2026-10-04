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

export const fmtDuration = (s: number | null | undefined): string => {
  if (s == null || Number.isNaN(s)) return "–";
  const t = Math.round(s);
  if (t < 60) return `${t} s`;
  if (t < 3600) return t % 60 === 0 ? `${t / 60} min` : `${Math.floor(t / 60)} min ${t % 60} s`;
  return `${Math.floor(t / 3600)} h ${Math.round((t % 3600) / 60)} min`;
};

/** The model to show for a call. The server's own answer wins; the policy's name is only the request, so it is labelled
 *  as such, and never presented as fact when the server did not confirm it. */
export function modelLabel(route: { model: string; served_model?: string | null }): string {
  const served = route.served_model;
  if (!served) return `${route.model} (as configured, the server did not say which model answered)`;
  return served === route.model ? served : `${served} (the policy asked for ${route.model})`;
}
