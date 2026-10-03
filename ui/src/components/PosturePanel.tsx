import type { PostureT } from "../api/types";

const RADIUS = 52;
const CIRC = 2 * Math.PI * RADIUS;

const fmtDelta = (d: number): string => (d < 0 ? `−${Math.abs(d)}` : `+${d}`);

/** The posture ring, and the explicit deduction line under the figures: no unexplained number. */
export function PosturePanel({ posture }: { posture: PostureT }) {
  const share = posture.max > 0 ? Math.max(0, Math.min(1, posture.score / posture.max)) : 0;
  return (
    <div className="score" role="img" aria-label={`Security posture ${posture.score} out of ${posture.max}`}>
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <circle className="trk" cx="60" cy="60" r={RADIUS} />
        <circle className="val" cx="60" cy="60" r={RADIUS} strokeDasharray={CIRC} strokeDashoffset={CIRC * (1 - share)} />
      </svg>
      <div className="num"><b>{posture.score}</b><span>Security posture</span></div>
    </div>
  );
}

export function DeductionLine({ posture }: { posture: PostureT }) {
  const controls = posture.controls_total != null && posture.controls_active != null
    ? `${posture.controls_active} of ${posture.controls_total} controls active. ` : "";
  return (
    <div className="deduct">
      <p className="faint">Share of the policy’s protection that is switched on. It is not a risk score.</p>
      {posture.breakdown.length === 0 ? (
        <p>{controls}No deductions. Signature feed current, AI models up, tests passing.</p>
      ) : (
        <p><b>{posture.score} of {posture.max}.</b> {controls}
          {posture.breakdown.map((b, i) => (
            <span key={b.item}>{i > 0 ? ", " : ""}<code>{b.item}</code> {b.note} ({fmtDelta(b.delta)})</span>
          ))}
        </p>
      )}
      {posture.formula && <p className="faint formula">{posture.formula}</p>}
    </div>
  );
}
