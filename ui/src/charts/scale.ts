/** Round a maximum up to a clean axis end (1, 2, 5, 10, 20, 50, ...). Never returns less than 1. */
export function niceMax(v: number): number {
  if (!Number.isFinite(v) || v <= 1) return 1;
  const pow = 10 ** Math.floor(Math.log10(v));
  for (const m of [1, 2, 5, 10]) if (v <= m * pow) return m * pow;
  return 10 * pow;
}

export const fmtCount = (n: number): string => n.toLocaleString("en-US");

/** Axis time label, local time, 24 h. */
export const fmtClock = (epochSeconds: number): string =>
  new Date(epochSeconds * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });

export const fmtDay = (epochSeconds: number): string =>
  new Date(epochSeconds * 1000).toLocaleDateString([], { month: "short", day: "numeric" });
