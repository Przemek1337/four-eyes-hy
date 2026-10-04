import { useEffect, useRef, useState } from "react";
import { useLive } from "../live";

export interface PollState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  /** when data last loaded successfully (ms since epoch) */
  updatedAt: number | null;
}

export function usePolling<T>(fetcher: () => Promise<T>, deps: unknown[] = [], intervalMs = 5000) {
  const { tick, report } = useLive();
  const [state, setState] = useState<PollState<T>>({ data: null, error: null, loading: true, updatedAt: null });
  const [manual, setManual] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const reportRef = useRef(report);
  reportRef.current = report;

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const data = await fetcherRef.current();
        if (cancelled) return;
        setState({ data, error: null, loading: false, updatedAt: Date.now() });
        reportRef.current(true);
      } catch (e) {
        if (cancelled) return;
        setState((s) => ({ ...s, error: (e as Error).message, loading: false }));
        reportRef.current(false);
      }
    };
    void run();
    const id = setInterval(run, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, manual, intervalMs]);

  return { ...state, refresh: () => setManual((m) => m + 1) };
}
