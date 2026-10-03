import type { CSSProperties, ReactNode } from "react";
import { fmtMs, fmtTime } from "../format";
import type { TimelineItem } from "../timeline";
import { Badge, DecisionPill } from "./Badge";

/** Vertical timeline. Each step is a big button that expands its details. Everything from the first untrusted
 *  step to the end sits in one tinted zone; a blocked step has a lime node with a cross, a held one a lime ring. */
export function Timeline({ items, expanded, onToggle, renderDetail }: {
  items: TimelineItem[];
  expanded: ReadonlySet<string>;
  onToggle: (key: string) => void;
  renderDetail?: (item: TimelineItem) => ReactNode;
}) {
  if (items.length === 0) return <p className="state">No steps recorded yet.</p>;
  const split = items.findIndex((i) => i.kind === "step" && i.tainted);
  const clean = split === -1 ? items : items.slice(0, split);
  const zone = split === -1 ? [] : items.slice(split);

  const renderItem = (it: TimelineItem, idx: number) => {
    if (it.kind === "note") {
      return (
        <li key={it.key} className="tl-note">
          <p><Badge tone={it.tone}>{it.title}</Badge> <span>{it.summary}</span></p>
        </li>
      );
    }
    const open = expanded.has(it.key);
    const cls = ["tl-step"];
    if (it.decision === "BLOCK") cls.push("stop");
    if (it.decision === "APPROVAL") cls.push("hold");
    if (open) cls.push("open");
    return (
      <li key={it.key} className={cls.join(" ")} style={{ "--i": idx } as CSSProperties}>
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
  };

  return (
    <ol className="tl" aria-label="Session timeline">
      {clean.map((it, i) => renderItem(it, i))}
      {zone.length > 0 && (
        <li className="tl-zone">
          <p className="tl-band">Session is untrusted from here</p>
          <ol className="tl-inner">{zone.map((it, i) => renderItem(it, clean.length + i))}</ol>
        </li>
      )}
    </ol>
  );
}
