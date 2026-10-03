export function Meter({ pct, level, label }: { pct: number | null; level: "ok" | "warn" | "over"; label: string }) {
  if (pct == null) return <span className="muted">no limit</span>;
  const clamped = Math.max(0, Math.min(100, Math.round(pct)));
  return (
    <div className="meter" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={clamped}>
      <div className={`meter-fill meter-${level}`} style={{ width: `${clamped}%` }} />
    </div>
  );
}
