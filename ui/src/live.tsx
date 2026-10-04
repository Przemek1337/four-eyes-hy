import { createContext, ReactNode, useCallback, useContext, useMemo, useRef, useState } from "react";
import { useEventStream } from "./hooks/useEventStream";

/** How many failed polls in a row, with no success in between, before the gateway counts as not responding. */
export const OFFLINE_AFTER = 3;

interface Live {
  tick: number;
  /** the event stream is open */
  connected: boolean;
  /** every recent poll failed: the gateway is not responding */
  offline: boolean;
  /** at least one poll has succeeded since the page opened (before that, nothing is on screen worth keeping) */
  loadedOnce: boolean;
  /** polling hooks tell the provider how each poll went */
  report: (ok: boolean) => void;
  /** refetch everything now */
  refreshNow: () => void;
}
const LiveContext = createContext<Live>({ tick: 0, connected: false, offline: false, loadedOnce: false, report: () => {}, refreshNow: () => {} });

export function LiveProvider({ children }: { children: ReactNode }) {
  const [tick, setTick] = useState(0);
  const [failures, setFailures] = useState(0);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const connected = useEventStream("/admin/stream", () => {
    window.clearTimeout(timer.current); // debounce bursts into one refresh
    timer.current = window.setTimeout(() => setTick((t) => t + 1), 250);
  });
  const report = useCallback((ok: boolean) => {
    setFailures((f) => (ok ? 0 : f + 1));
    if (ok) setLoadedOnce(true);
  }, []);
  const refreshNow = useCallback(() => setTick((t) => t + 1), []);
  const offline = failures >= OFFLINE_AFTER;
  const value = useMemo(() => ({ tick, connected, offline, loadedOnce, report, refreshNow }),
    [tick, connected, offline, loadedOnce, report, refreshNow]);
  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}

export const useLive = () => useContext(LiveContext);
