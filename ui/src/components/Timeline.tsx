import type { CSSProperties, ReactNode } from "react";
import { fmtMs, fmtTime } from "../format";
import type { TimelineItem } from "../timeline";
import { Badge, DecisionPill } from "./Badge";

/** Vertical timeline. Each step is a big button that expands its details. Steps after the first untrusted
 *  one sit on a tinted band; a blocked step has a lime node with a cross; a held one has a lime ring. */
export function Timeline({ items, expanded, onToggle, renderDetail }: {
  items: TimelineItem[];
  expanded: ReadonlySet<string>;
  onToggle: (key: string) => void;
  renderDetail?: (item: TimelineItem) => ReactNode;
}) {
  if (items.length === 0) return <p className="state">No steps recorded yet.</p>;
  const steps = items.filter((i) => i.kind === "step");
  const firstDirty = steps.find((s) => s.tainted)?.key;
  const lastStep = steps[steps.length - 1]?.key;
  return (
    <ol className="tl" aria-label="Session timeline">
      {items.map((it, idx) => {
        if (it.kind === "note") {
          return (
            <li key={it.key} className="tl-note">
              <Badge tone={it.tone}>{it.title}</Badge> <span>{it.summary}</span>
            </li>
          );
        }
        const open = expanded.has(it.key);
        const cls = ["tl-step"];
        if (it.tainted) cls.push("dirty");
        if (it.key === firstDirty) cls.push("first");
        if (it.tainted && it.key === lastStep) cls.push("last");
        if (it.decision === "BLOCK") cls.push("stop");
        if (it.decision === "APPROVAL") cls.push("hold");
        if (open) cls.push("open");
        return (
          <li key={it.key} className={cls.join(" ")} style={{ "--i": idx } as CSSProperties}>
            {it.key === firstDirty && <span className="tl-band">Session is untrusted from here</span>}
            <span className="tl-node" aria-hidden="true" />
            <div className="tl-body">
              <button className="tl-btn" aria-expanded={open} onClick={() => onToggle(it.key)}>
                <span className="tl-main">
                  <span className="tl-head"><strong>{it.title}</strong> <DecisionPill decision={it.decision} /></span>
                  <span className="tl-sum">{it.summary}</span>
                </span>
                <span className="tl-toggle">{open ? "Hide details" : "Show details"}<i aria-hidden="true" /></span>
              </button>
              {open && <div className="tl-detail">{renderDetail?.(it)}</div>}
            </div>
            <time className="tl-time">{fmtTime(it.ts)}<small>{fmtMs(it.ms)}{it.route ? ` · ${it.route}` : ""}</small></time>
          </li>
        );
      })}
    </ol>
  );
}
