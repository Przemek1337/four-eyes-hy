import { render, screen, within } from "@testing-library/react";
import { fx } from "../test/fixtures";
import { BudgetsPanel } from "./BudgetsPanel";
import { SpeedPanel } from "./SpeedPanel";
import { TestsPanel } from "./TestsPanel";

describe("BudgetsPanel", () => {
  const cost = { local_usd: 0, external_usd: 0.84, compute_s: 42.3 };

  it("shows a bar per agent and team with words for the level and the counters", () => {
    const { container } = render(<BudgetsPanel budgets={fx.budgets()} cost={cost} />);
    expect(screen.getByRole("progressbar", { name: "kyc-agent budget" })).toHaveAttribute("aria-valuenow", "56");
    expect(screen.getByText(/\$1\.12 \/ \$2\.00/)).toBeInTheDocument();
    expect(screen.getByText("near limit")).toBeInTheDocument();
    expect(screen.getByText("limit reached")).toBeInTheDocument();
    expect(container.querySelector(".meter-warn")).not.toBeNull();
    expect(container.querySelector(".meter-over")).not.toBeNull();
    expect(screen.getByRole("progressbar", { name: "compliance budget" })).toBeInTheDocument();
    expect(screen.getByText(/4 blocked by budget · 2 routed to the local model/)).toBeInTheDocument();
  });

  it("shows tokens and compute for each agent", () => {
    render(<BudgetsPanel budgets={fx.budgets()} cost={cost} />);
    expect(screen.getByText("210 of 600 compute seconds · 8,420 tokens today")).toBeInTheDocument();
    expect(screen.getByText("12 compute seconds · 6,130 tokens today")).toBeInTheDocument();
  });

  it("tells when the limit would be reached at the current pace, or that it is safe", () => {
    render(<BudgetsPanel budgets={fx.budgets()} cost={cost} />);
    expect(screen.getByText(/Spending \$0\.3100 an hour\. At this pace the limit is reached at \d\d:\d\d\./)).toBeInTheDocument();
    expect(screen.getAllByText(/Within budget at this pace\./).length).toBe(2); // playground-agent and the team
    expect(screen.getByText("Limit reached. New requests are blocked or rerouted.")).toBeInTheDocument();
  });

  it("handles agents without any limit and omits a pace it cannot know", () => {
    render(<BudgetsPanel budgets={fx.budgets()} cost={cost} />);
    expect(screen.getByText(/\$0\.0000 · no USD limit/)).toBeInTheDocument();
    expect(screen.queryByText(/Spending \$0\.0000/)).not.toBeInTheDocument();
  });

  it("shows the per-session limit with the busiest session", () => {
    render(<BudgetsPanel budgets={fx.budgets()} cost={cost} />);
    expect(screen.getByText("max 20,000 tokens, 20 steps")).toBeInTheDocument();
    expect(screen.getByText(/Busiest session: 6,800 of 20,000 tokens, 7 of 20 steps · 1 stopped by a limit/)).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Per session budget" })).toHaveAttribute("aria-valuenow", "34");
  });

  it("shows the cost split and an empty state", () => {
    render(<BudgetsPanel budgets={{ agents: [], teams: [], blocked_by_budget: 0, fallbacks: 0 }} cost={cost} />);
    expect(screen.getByText("No budgets configured.")).toBeInTheDocument();
    expect(screen.getByText(/external \$0\.8400 · local \$0\.0000 · 42\.3 s compute/)).toBeInTheDocument();
  });
});

describe("SpeedPanel", () => {
  const m = fx.metrics();
  it("shows load and gateway p95 as two separate charts, never one chart with two axes", () => {
    render(<SpeedPanel latency={m.latency} series={fx.timeseries()} throughput={42} />);
    expect(screen.getByRole("img", { name: /^Requests:/ })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /^Gateway p95:/ })).toBeInTheDocument();
    expect(screen.getByText(/Throughput now: 42 requests a minute\./)).toBeInTheDocument();
    expect(screen.getAllByRole("img")).toHaveLength(2);
  });

  it("puts the gateway's cost next to the model's and says how big the layer's share is", () => {
    render(<SpeedPanel latency={m.latency} series={fx.timeseries()} />);
    expect(screen.getByText(/The layer is 1\.5% of end-to-end time at p95/)).toBeInTheDocument();
    const rows = screen.getAllByRole("listitem");
    expect(rows[0]).toHaveTextContent("Gateway, median");
    expect(rows[0]).toHaveTextContent("6.0 ms");
    expect(rows[3]).toHaveTextContent("Model or tool, p95");
    expect(rows[3]).toHaveTextContent("1200 ms");
    expect(rows[1].querySelector(".lead")).not.toBeNull(); // only the gateway p95 bar is in the accent
    expect(rows[3].querySelector(".lead")).toBeNull();
  });

  it("lists rule vs AI check time and the slowest controls", () => {
    render(<SpeedPanel latency={m.latency} series={null} />);
    expect(screen.getByText("Rule checks p50 / p95").nextSibling).toHaveTextContent("1.0 ms / 3.0 ms");
    expect(screen.getByText("AI checks p50 / p95").nextSibling).toHaveTextContent("100 ms / 140 ms");
    const slow = screen.getAllByRole("listitem").filter((li) => li.querySelector("code"));
    expect(slow[0]).toHaveTextContent("sem.prompt_injection");
  });

  it("copes with no traffic and no series", () => {
    const zero = { count: 0, p50: 0, p95: 0 };
    render(<SpeedPanel latency={{ controls: {}, layers: { det: zero, ai: zero }, gateway: zero, upstream: zero }} series={null} />);
    expect(screen.getAllByText("–").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText("No control timings yet.")).toBeInTheDocument();
    expect(screen.getByText("No latency recorded in this window yet.")).toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain("NaN");
  });

  it("skips empty hours when drawing the p95 line", () => {
    const series = fx.timeseries();
    series.points[2].gateway_p95_ms = null;
    render(<SpeedPanel latency={m.latency} series={series} />);
    expect(screen.getByRole("img", { name: /^Gateway p95:/ })).toBeInTheDocument();
  });
});

describe("TestsPanel", () => {
  it("shows passed tests with the positive and negative split and zero missed attacks and false blocks", () => {
    render(<TestsPanel tests={fx.tests()} />);
    const panel = screen.getByRole("region", { name: "Test suite" });
    expect(within(panel).getByRole("group", { name: "Tests passed" })).toHaveTextContent("142 / 142");
    expect(within(panel).getByRole("group", { name: "Tests passed" })).toHaveTextContent("71 allowed cases · 71 stopped cases");
    expect(within(panel).getByRole("group", { name: "Missed attacks" })).toHaveTextContent("0");
    expect(within(panel).getByRole("group", { name: "Missed attacks" })).toHaveClass("hold");
    expect(within(panel).getByRole("group", { name: "False blocks" })).toHaveClass("hold");
    expect(within(panel).getByText("make test")).toBeInTheDocument();
  });

  it("calls out missed attacks and false blocks when they are not zero", () => {
    render(<TestsPanel tests={fx.tests({ missed_attacks: 2, false_blocks: 1, passed: 140, failed: 3 })} />);
    const missed = screen.getByRole("group", { name: "Missed attacks" });
    expect(missed).not.toHaveClass("hold");
    expect(missed).toHaveTextContent("Gap");
    expect(screen.getByRole("group", { name: "False blocks" })).toHaveTextContent("Gap");
    expect(screen.getByRole("group", { name: "Tests passed" })).toHaveTextContent("140 / 143");
  });

  it("shows results by OWASP category and marks failing ones", () => {
    render(<TestsPanel tests={fx.tests()} />);
    expect(screen.getByText("Results by OWASP category")).toBeInTheDocument();
    expect(screen.getByText("LLM04:2026").closest("tr")).toHaveTextContent("2 / 3");
    expect(screen.getByText("2 / 3")).toHaveClass("bad");
    expect(screen.getByText("6 / 6")).not.toHaveClass("bad");
  });

  it("tells how to produce a report when there is none", () => {
    render(<TestsPanel tests={fx.tests({ ran_at: null, passed: 0, failed: 0, by_owasp: {} })} />);
    expect(screen.getByText(/No test report yet/)).toBeInTheDocument();
    expect(screen.getByText("make test")).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Missed attacks" })).not.toBeInTheDocument();
  });
});
