import type { ReactNode } from "react";

interface State<T> { data: T | null; error: string | null; loading: boolean }

export function Async<T>({ state, isEmpty, emptyText = "Nothing to show yet.", children }: {
  state: State<T>;
  isEmpty?: (data: T) => boolean;
  emptyText?: string;
  children: (data: T) => ReactNode;
}) {
  const { data, error, loading } = state;
  if (data == null) {
    if (error) return <p role="alert" className="state state-error">Could not load: {error}</p>;
    return <p className="state">{loading ? "Loading…" : emptyText}</p>;
  }
  return (
    <>
      {error && <p role="status" className="state state-warn">Showing the last data; refresh failed: {error}</p>}
      {isEmpty?.(data) ? <p className="state">{emptyText}</p> : children(data)}
    </>
  );
}
