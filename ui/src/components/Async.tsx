import type { ReactNode } from "react";
import { fmtTime } from "../format";

interface State<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  updatedAt?: number | null;
  refresh?: () => void;
}

function Retry({ onRetry }: { onRetry?: () => void }) {
  return onRetry ? <button className="btn-sm retry" onClick={onRetry}>Retry</button> : null;
}

/** Loading, failed, late and empty states for one panel. A skeleton holds the layout while loading; stale data stays visible. */
export function Async<T>({ state, isEmpty, emptyText = "Nothing to show yet.", children }: {
  state: State<T>;
  isEmpty?: (data: T) => boolean;
  emptyText?: string;
  children: (data: T) => ReactNode;
}) {
  const { data, error, loading, updatedAt, refresh } = state;
  if (data == null) {
    if (error) {
      return (
        <div className="state-box" role="alert">
          <span>Could not load: {error}</span>
          <Retry onRetry={refresh} />
        </div>
      );
    }
    if (loading) {
      return (
        <div className="skeleton" role="status" aria-busy="true">
          <span className="sr-only">Loading…</span>
          <i /><i /><i />
        </div>
      );
    }
    return <p className="state">{emptyText}</p>;
  }
  return (
    <>
      {error && (
        <div className="state-box late" role="status">
          <span>
            {updatedAt ? `Showing the last data from ${fmtTime(new Date(updatedAt).toISOString())}` : "Showing the last data"}; refresh failed: {error}
          </span>
          <Retry onRetry={refresh} />
        </div>
      )}
      {isEmpty?.(data) ? <p className="state">{emptyText}</p> : children(data)}
    </>
  );
}
