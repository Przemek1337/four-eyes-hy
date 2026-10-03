import type { BudgetsT, Metrics } from "../api/types";
import { fmtCount, fmtClock } from "../charts/scale";
import { fmtUsd } from "../format";
import { Meter } from "./Meter";

type Level = "ok" | "warn" | "over";

const LEVEL_TEXT: Record<Level, string | null> = { ok: null, warn: "near limit", over: "limit reached" };

/** Says when the limit would be reached at the current pace, or that the budget is safe. Words, not colour. */
function pace(level: Level, perHour: number | undefined, exhaustAt: number | null | undefined, hasLimit: boolean): string | null {
  if (!hasLimit) return "no USD limit";
  if (level === "over") return "Limit reached. New requests are blocked or rerouted.";
  if (perHour == null) return null;
  const rate = `Spending ${fmtUsd(perHour)} an hour.`;
  return exhaustAt != null ? `${rate} At this pace the limit is reached at ${fmtClock(exhaustAt)}.` : `${rate} Within budget at this pace.`;
}

function Row({ name, used, limit, pct, level, detail, paceText, headline }: {
  name: string; used: number; limit: number | null; pct: number | null; level: Level; detail?: string; paceText: string | null; headline?: string;
}) {
  const note = LEVEL_TEXT[level];
  return (
    <div className="bud">
      <div className="bar-h">
        <b>{name}</b>
        <span>{headline ?? (limit == null ? `${fmtUsd(used)} · no USD limit` : `${fmtUsd(used)} / ${fmtUsd(limit)}`)}{note && <em className={`lvl ${level}`}>{note}</em>}</span>
      </div>
      <Meter pct={pct} level={level} label={`${name} budget`} />
      {detail && <div className="bar-f">{detail}</div>}
      {paceText && paceText !== "no USD limit" && <div className="bar-f">{paceText}</div>}
    </div>
  );
}

/** What it costs and who is near a limit: USD, compute seconds and tokens, with the pace each budget is burning at. */
export function BudgetsPanel({ budgets, cost }: { budgets: BudgetsT; cost: Metrics["cost"] }) {
  const sl = budgets.session_limits;
  const empty = budgets.agents.length === 0 && budgets.teams.length === 0 && !sl;
  return (
    <section className="sec" aria-label="Budgets and cost">
      <h2>Cost</h2>
      <p className="sub">What it costs, and who is near a limit? Daily per agent, monthly per team. Above the soft limit raises an alert.</p>
      {empty ? <p className="state">No budgets configured.</p> : (
        <div className="bars">
          {budgets.agents.map((a) => (
            <Row key={a.agent} name={a.agent} used={a.usd_used} limit={a.usd_limit} pct={a.pct} level={a.level}
                 detail={[
                   a.compute_limit != null ? `${fmtCount(Math.round(a.compute_used))} of ${fmtCount(a.compute_limit)} compute seconds` : `${fmtCount(Math.round(a.compute_used))} compute seconds`,
                   a.tokens_used != null ? `${fmtCount(a.tokens_used)} tokens today` : null,
                 ].filter(Boolean).join(" · ")}
                 paceText={pace(a.level, a.usd_per_hour, a.projected_exhaust_at, a.usd_limit != null)} />
          ))}
          {budgets.teams.map((t) => (
            <Row key={t.team} name={t.team} used={t.usd_used} limit={t.usd_limit} pct={t.pct} level={t.level}
                 detail="Team budget, this month"
                 paceText={pace(t.level, t.usd_per_hour, t.projected_exhaust_at, t.usd_limit != null)} />
          ))}
          {sl && (
            <Row name="Per session" used={0} limit={null} headline={`max ${fmtCount(sl.max_tokens)} tokens, ${sl.max_steps} steps`} pct={sl.max_tokens > 0 ? (sl.busiest.tokens / sl.max_tokens) * 100 : null}
                 level={sl.max_tokens > 0 && sl.busiest.tokens / sl.max_tokens >= 0.8 ? "warn" : "ok"}
                 detail={`Busiest session: ${fmtCount(sl.busiest.tokens)} of ${fmtCount(sl.max_tokens)} tokens, ${sl.busiest.steps} of ${sl.max_steps} steps · ${sl.stopped_by_limit} stopped by a limit`}
                 paceText={null} />
          )}
        </div>
      )}
      <p className="cost-line">
        Spent: external {fmtUsd(cost.external_usd)} · local {fmtUsd(cost.local_usd)} · {cost.compute_s.toFixed(1)} s compute.{" "}
        {budgets.blocked_by_budget} blocked by budget · {budgets.fallbacks} routed to the local model.
      </p>
    </section>
  );
}
