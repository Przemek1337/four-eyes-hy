import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { AttackStatusT } from "../api/types";

const POLL_MS = 1000;

/** "Run test attack": a staged mix of attacks and legitimate requests, one at a time, so the dashboard visibly changes. */
export function AttackDemoBar({ pollMs = POLL_MS }: { pollMs?: number }) {
  const [status, setStatus] = useState<AttackStatusT | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const running = status?.state === "running";

  const refresh = async () => {
    try {
      setStatus(await api.attackStatus());
    } catch (e) {
      setError((e as Error).message);
    }
  };

  useEffect(() => { void refresh(); }, []);                 // pick up a run that is already going
  useEffect(() => {
    if (!running) return undefined;
    timer.current = window.setInterval(() => void refresh(), pollMs);
    return () => window.clearInterval(timer.current);
  }, [running, pollMs]);

  const start = async () => {
    setError(null);
    try {
      setStatus(await api.startAttack());
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) void refresh();          // already running: just follow it
      else setError((e as Error).message);
    }
  };

  const unavailable = status?.state === "unavailable";
  const s = status?.summary;
  // One line, whatever the state, so the card never changes height and the page below does not jump.
  const line = running ? (
    <><b>{status?.sent ?? 0} sent</b>{status?.current && <> · now: {status.current.label} <span className="mono">{status.current.actual}</span></>}</>
  ) : status?.state === "done" && s ? (
    <>Finished: {s.attacks_stopped} of {s.attacks} attacks stopped, {s.legit_passed} of {s.legit} normal requests passed.
      {s.unexpected.length > 0 && <span className="state-warn"> Unexpected: {s.unexpected.join("; ")}</span>}</>
  ) : unavailable ? (
    "Needs the demo harness. Start the gateway with make run."
  ) : (
    "Sends attacks and normal requests one at a time. Watch Security and Management change."
  );
  return (
    <section className="attackbar" aria-label="Test attack">
      <div className="ab-row">
        <div className="ab-text">
          <b>Test attack</b>
          <p className="ab-line" role="status" aria-live="polite" title={running && status?.current ? status.current.label : undefined}>{line}</p>
        </div>
        <button className="btn-sm ab-run" disabled={running || unavailable} onClick={() => void start()}>
          {running ? "Attack running…" : "Run test attack"}
        </button>
      </div>
      {status?.state === "failed" && <p role="alert" className="state state-error">The run stopped: {status.error}</p>}
      {error && <p role="alert" className="state state-error">{error}</p>}
    </section>
  );
}
