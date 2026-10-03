import { createContext, ReactNode, useContext, useMemo, useRef, useState } from "react";
import { useEventStream } from "./hooks/useEventStream";

interface Live { tick: number; connected: boolean }
const LiveContext = createContext<Live>({ tick: 0, connected: false });

export function LiveProvider({ children }: { children: ReactNode }) {
  const [tick, setTick] = useState(0);
  const timer = useRef<number | undefined>(undefined);
  const connected = useEventStream("/admin/stream", () => {
    window.clearTimeout(timer.current); // debounce bursts into one refresh
    timer.current = window.setTimeout(() => setTick((t) => t + 1), 250);
  });
  const value = useMemo(() => ({ tick, connected }), [tick, connected]);
  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}

export const useLive = () => useContext(LiveContext);
