import { useMemo, useState } from "react";
import { api } from "../api/client";
import type { SessionDetailT } from "../api/types";
import { usePolling } from "../hooks/usePolling";
import { buildTimeline, headlineFor, taintedFrom } from "../timeline";
import { Async } from "./Async";
import { FlowMap } from "./FlowMap";
import { SessionHeader } from "./SessionHeader";
import { Timeline } from "./Timeline";
import { WhyBlocked } from "./WhyBlocked";

function Detail({ data }: { data: SessionDetailT }) {
  const items = useMemo(() => buildTimeline(data.events), [data.events]);
  const steps = items.filter((i) => i.kind === "step");
  const defaultKey = [...steps].reverse().find((s) => s.tone === "red")?.key ?? steps[steps.length - 1]?.key ?? null;
  const [picked, setPicked] = useState<string | null>(null);
  const key = picked && steps.some((s) => s.key === picked) ? picked : defaultKey;
  const approvalFor = (ev: SessionDetailT["events"][number]) => {
    const id = ev.detail?.approval_id as string | undefined;
    return data.approvals.find((a) => a.id === id) ?? null;
  };
  return (
    <>
      <SessionHeader session={data.session} headline={headlineFor(data.session, items)} taintedFrom={taintedFrom(items)} />
      {data.flow && <FlowMap flow={data.flow} />}
      <Timeline
        items={items}
        selectedKey={key}
        onSelect={setPicked}
        renderDetail={(it) => <WhyBlocked event={it.event} approval={approvalFor(it.event)} />}
      />
    </>
  );
}

export function SessionDetail({ sessionId }: { sessionId: string; onDecided?: () => void }) {
  const state = usePolling(() => api.session(sessionId), [sessionId]);
  return (
    <section aria-label="Session detail" className="detail">
      <Async state={state} emptyText="Session not found.">{(data) => <Detail data={data} />}</Async>
    </section>
  );
}
