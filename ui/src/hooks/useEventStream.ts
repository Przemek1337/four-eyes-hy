import { useEffect, useRef, useState } from "react";

export function useEventStream(url: string, onEvent: (event: unknown) => void): boolean {
  const [connected, setConnected] = useState(false);
  const handler = useRef(onEvent);
  handler.current = onEvent;

  useEffect(() => {
    if (typeof EventSource === "undefined") return;
    const es = new EventSource(url);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false); // the browser reconnects by itself; polling covers the gap
    es.onmessage = (m: MessageEvent<string>) => {
      try {
        handler.current(JSON.parse(m.data));
      } catch {
        /* ignore malformed frames */
      }
    };
    return () => es.close();
  }, [url]);

  return connected;
}
