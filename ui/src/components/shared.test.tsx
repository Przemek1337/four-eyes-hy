import { render, screen } from "@testing-library/react";
import { Async } from "./Async";
import { Badge, DecisionPill, StatusMark } from "./Badge";
import { Meter } from "./Meter";
import { Panel } from "./Panel";

describe("Badge and DecisionPill", () => {
  it("renders text with a tone class", () => {
    render(<Badge tone="red">blocked</Badge>);
    expect(screen.getByText("blocked")).toHaveClass("badge", "badge-red");
  });
  it("renders a pill per decision and a dash when absent", () => {
    const { rerender } = render(<DecisionPill decision="APPROVAL" />);
    expect(screen.getByText("APPROVAL")).toHaveClass("badge-yellow");
    rerender(<DecisionPill decision="BLOCK" />);
    expect(screen.getByText("BLOCK")).toHaveClass("badge-red");
    rerender(<DecisionPill decision={null} />);
    expect(screen.getByText("–")).toBeInTheDocument();
  });
});

describe("StatusMark", () => {
  it("pairs a mark with a word for each session status", () => {
    const { rerender, container } = render(<StatusMark status="clean" />);
    expect(screen.getByText("Clean")).toBeInTheDocument();
    expect(container.querySelector(".st")).not.toHaveClass("untrusted");
    rerender(<StatusMark status="untrusted" />);
    expect(container.querySelector(".st")).toHaveClass("untrusted");
    rerender(<StatusMark status="high_risk" />);
    expect(screen.getByText("High risk")).toBeInTheDocument();
    expect(container.querySelector(".st")).toHaveClass("risk");
  });
});

describe("Panel", () => {
  it("is a labelled region with a title and actions", () => {
    render(<Panel title="Budgets" actions={<button>Go</button>}>body</Panel>);
    expect(screen.getByRole("region", { name: "Budgets" })).toHaveTextContent("body");
    expect(screen.getByRole("button", { name: "Go" })).toBeInTheDocument();
  });
});

describe("Meter", () => {
  it("exposes the percentage and level, clamps it and handles a missing limit", () => {
    const { rerender } = render(<Meter pct={72.4} level="ok" label="Onboarding" />);
    const bar = screen.getByRole("progressbar", { name: "Onboarding" });
    expect(bar).toHaveAttribute("aria-valuenow", "72");
    rerender(<Meter pct={250} level="over" label="Onboarding" />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
    rerender(<Meter pct={null} level="ok" label="Onboarding" />);
    expect(screen.getByText("no limit")).toBeInTheDocument();
  });
});

describe("Async", () => {
  const view = (d: string[]) => <ul>{d.map((x) => <li key={x}>{x}</li>)}</ul>;
  it("shows loading, then an error without data", () => {
    const { rerender } = render(<Async state={{ data: null, error: null, loading: true }}>{view}</Async>);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    rerender(<Async state={{ data: null, error: "backend down", loading: false }}>{view}</Async>);
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load: backend down");
  });
  it("keeps showing stale data with a warning when a refresh fails", () => {
    render(<Async<string[]> state={{ data: ["a"], error: "timeout", loading: false }}>{view}</Async>);
    expect(screen.getByText("a")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("refresh failed: timeout");
  });
  it("shows an empty message for empty data", () => {
    render(<Async<string[]> state={{ data: [], error: null, loading: false }} isEmpty={(d) => d.length === 0} emptyText="No sessions yet.">{view}</Async>);
    expect(screen.getByText("No sessions yet.")).toBeInTheDocument();
  });
});
