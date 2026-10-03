import { useMemo, useState } from "react";
import { api } from "../api/client";
import type { SessionDetailT } from "../api/types";
import { usePolling } from "../hooks/usePolling";
import { buildTimeline, headlineFor, taintedFrom } from "../timeline";
import { ApprovalCard } from "./ApprovalCard";
import { Async } from "./Async";
import { FlowMap } from "./FlowMap";
import { SessionHeader } from "./SessionHeader";
import { Timeline } from "./Timeline";
import { WhyBlocked } from "./WhyBlocked";

function Detail({ data, onDecided }: { data: SessionDetailT; onDecided: () => void }) {
  const items = useMemo(() => buildTimeline(data.events), [data.events]);
  const steps = items.filter((i) => i.kind === "step");
  // Until the user touches anything, the steps FourEyes stopped or held are open: that is the story.
  const [picked, setPicked] = useState<Set<string> | null>(null);
  const expanded = picked ?? new Set(steps.filter((s) => s.decision === "BLOCK" || s.decision === "APPROVAL").map((s) => s.key));
  const toggle = (key: string) => {
    const next = new Set(expanded);
    if (next.has(key)) next.delete(key); else next.add(key);
    setPicked(next);
  };
  const allOpen = steps.length > 0 && steps.every((s) => expanded.has(s.key));
  const approvalFor = (ev: SessionDetailT["events"][number]) => {
    const id = ev.detail?.approval_id as string | undefined;
    return data.approvals.find((a) => a.id === id) ?? null;
  };
  // Pending approvals first; decided ones stay visible so the outcome does not vanish on the next refresh.
  const approvals = [...data.approvals].sort((a, b) => Number(b.status === "pending") - Number(a.status === "pending"));
  const main = (
    <>
      <SessionHeader session={data.session} headline={headlineFor(data.session, items)} taintedFrom={taintedFrom(items)} />
      {data.flow && <FlowMap flow={data.flow} />}
      {steps.length > 0 && (
        <div className="tl-tools">
          <h2>What happened, step by step</h2>
          <button className="btn-sm" onClick={() => setPicked(allOpen ? new Set() : new Set(steps.map((s) => s.key)))}>
            {allOpen ? "Collapse all" : "Expand all"}
          </button>
        </div>
      )}
      <Timeline
        items={items}
        expanded={expanded}
        onToggle={toggle}
        renderDetail={(it) => <WhyBlocked event={it.event} approval={approvalFor(it.event)} />}
      />
    </>
  );
  if (approvals.length === 0) return main;
  return (
    <div className="split">
      <div className="detail-main">{main}</div>
      <aside className="review-col" aria-label="Approvals">
        {approvals.map((a) => <ApprovalCard key={a.id} approval={a} onDecided={onDecided} />)}
      </aside>
    </div>
  );
}

export function SessionDetail({ sessionId, onDecided }: { sessionId: string; onDecided?: () => void }) {
  const state = usePolling(() => api.session(sessionId), [sessionId]);
  const decided = () => {
    state.refresh();
    onDecided?.();
  };
  return (
    <section aria-label="Session detail" className="detail">
      <Async state={state} emptyText="Session not found.">{(data) => <Detail data={data} onDecided={decided} />}</Async>
    </section>
  );
}
