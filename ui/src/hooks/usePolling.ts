import { useEffect, useRef, useState } from "react";
import { useLive } from "../live";

export interface PollState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

export function usePolling<T>(fetcher: () => Promise<T>, deps: unknown[] = [], intervalMs = 5000) {
  const { tick } = useLive();
  const [state, setState] = useState<PollState<T>>({ data: null, error: null, loading: true });
  const [manual, setManual] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const data = await fetcherRef.current();
        if (!cancelled) setState({ data, error: null, loading: false });
      } catch (e) {
        if (!cancelled) setState((s) => ({ ...s, error: (e as Error).message, loading: false }));
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
