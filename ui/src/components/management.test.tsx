import { render, screen } from "@testing-library/react";
import { fx } from "../test/fixtures";
import { KpiRow } from "./KpiRow";
import { OwaspPanel } from "./OwaspPanel";
import { DeductionLine, PosturePanel } from "./PosturePanel";

describe("KpiRow", () => {
  it("shows the eight figures with readable numbers", () => {
    render(<KpiRow metrics={fx.metrics()} />);
    expect(screen.getByRole("group", { name: "Requests" })).toHaveTextContent("1,284");
    expect(screen.getByRole("group", { name: "Allowed" })).toHaveTextContent("1,102");
    expect(screen.getByRole("group", { name: "Redacted" })).toHaveTextContent("61");
    expect(screen.getByRole("group", { name: "Sent for approval" })).toHaveTextContent("3");
    expect(screen.getByRole("group", { name: "Blocked" })).toHaveClass("hold");
    expect(screen.getByRole("group", { name: "Blocked" })).toHaveTextContent("118");
    expect(screen.getByRole("group", { name: "Approvals open" })).toHaveTextContent("1");
    const spent = screen.getByRole("group", { name: "Spent" });
    expect(spent).toHaveTextContent("$0.8400");
    expect(spent).toHaveTextContent("42.3 s compute");
  });

  it("keeps the private → external invariant calm at zero and loud above it", () => {
    const { rerender } = render(<KpiRow metrics={fx.metrics()} />);
    const calm = screen.getByRole("group", { name: "Private → external" });
    expect(calm).toHaveTextContent("0");
    expect(screen.queryByText("Breach")).not.toBeInTheDocument();
    rerender(<KpiRow metrics={fx.metrics({ private_to_external: 3 })} />);
    expect(screen.getByRole("group", { name: "Private → external" })).toHaveTextContent("Breach");
    expect(screen.getByText(/must stay at 0/)).toBeInTheDocument();
  });

  it("copes with an empty gateway", () => {
    const empty = fx.metrics({ requests: 0, by_decision: { ALLOW: 0, REDACT: 0, APPROVAL: 0, BLOCK: 0 }, open_approvals: 0,
      cost: { local_usd: 0, external_usd: 0, compute_s: 0 } });
    render(<KpiRow metrics={empty} />);
    expect(screen.getByRole("group", { name: "Requests" })).toHaveTextContent("0");
    expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
  });
});

describe("PosturePanel", () => {
  it("draws the ring for the score with an accessible label", () => {
    const { container } = render(<PosturePanel posture={fx.posture({ score: 90, breakdown: [] })} />);
    expect(screen.getByRole("img", { name: "Security posture 90 out of 100" })).toBeInTheDocument();
    const val = container.querySelector(".val") as SVGCircleElement;
    const circ = 2 * Math.PI * 52;
    expect(Number(val.getAttribute("stroke-dashoffset"))).toBeCloseTo(circ * 0.1, 3);
  });
  it("clamps nonsense scores and a zero maximum", () => {
    const { container, rerender } = render(<PosturePanel posture={fx.posture({ score: 250, max: 100 })} />);
    expect(Number((container.querySelector(".val") as Element).getAttribute("stroke-dashoffset"))).toBe(0);
    rerender(<PosturePanel posture={fx.posture({ score: 5, max: 0 })} />);
    expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
  });
});

describe("DeductionLine", () => {
  it("names every deduction with its note and amount, plus the formula", () => {
    render(<DeductionLine posture={fx.posture({ breakdown: [
      { item: "dlp.redact_inflight", delta: -10, note: "removed" }, { item: "signature feed", delta: -10, note: "error" }] })} />);
    expect(screen.getByText(/90 of 100/)).toBeInTheDocument();
    expect(screen.getByText("dlp.redact_inflight")).toBeInTheDocument();
    expect(screen.getByText(/removed \(−10\)/)).toBeInTheDocument();
    expect(screen.getByText(/error \(−10\)/)).toBeInTheDocument();
    expect(screen.getByText(/score = 100/)).toBeInTheDocument();
  });
  it("says so when nothing is deducted", () => {
    render(<DeductionLine posture={fx.posture({ breakdown: [], score: 100 })} />);
    expect(screen.getByText(/No deductions\./)).toBeInTheDocument();
  });
});

describe("OwaspPanel", () => {
  it("shows the edition, the tested counter, the counts per status and a tile per category", () => {
    render(<OwaspPanel owasp={fx.owasp()} />);
    expect(screen.getByRole("heading", { name: "OWASP LLM Top 10 (2026): 10/10 categories tested" })).toBeInTheDocument();
    expect(screen.getByText(/1 enforced, 1 monitor only, 1 uncovered/)).toBeInTheDocument();
    const enforced = screen.getByRole("group", { name: "LLM01:2026" });
    expect(enforced).toHaveTextContent("41 blocked");
    expect(enforced.querySelector(".cov")).not.toHaveClass("mon", "unc");
    const monitor = screen.getByRole("group", { name: "LLM02:2026" });
    expect(monitor.querySelector(".cov")).toHaveClass("mon");
    expect(monitor).toHaveTextContent("monitor only");
    const gap = screen.getByRole("group", { name: "LLM07:2026" });
    expect(gap.querySelector(".cov")).toHaveClass("unc");
    expect(gap).toHaveTextContent("uncovered");
    expect(gap).toHaveTextContent("no grounding control");
  });
  it("leaves out the uncovered count when everything is covered", () => {
    render(<OwaspPanel owasp={fx.owasp({ categories: [fx.owasp().categories[0]] })} />);
    expect(screen.getByText(/1 enforced, 0 monitor only\./)).toBeInTheDocument();
    expect(screen.queryByText(/uncovered/)).not.toBeInTheDocument();
  });
});
