import type { ReactNode } from "react";

export function Panel({ title, actions, children }: { title: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="panel" aria-label={title}>
      <header>
        <h3>{title}</h3>
        {actions}
      </header>
      {children}
    </section>
  );
}
