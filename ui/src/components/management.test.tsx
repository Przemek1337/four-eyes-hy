import { render, screen } from "@testing-library/react";
import { fx } from "../test/fixtures";
import { DataProtectionPanel } from "./DataProtectionPanel";
import { KpiRow } from "./KpiRow";
import { OwaspPanel } from "./OwaspPanel";
import { DeductionLine, PosturePanel } from "./PosturePanel";
import { ThreatsPanel } from "./ThreatsPanel";

describe("KpiRow", () => {
  it("shows the five figures with readable numbers and where they come from", () => {
    render(<KpiRow metrics={fx.metrics()} />);
    const requests = screen.getByRole("group", { name: "Requests" });
    expect(requests).toHaveTextContent("1,284");
    expect(requests).toHaveTextContent("1,102 allowed · 61 redacted · 3 for approval");
    const blocked = screen.getByRole("group", { name: "Blocked" });
    expect(blocked).toHaveClass("hold");
    expect(blocked).toHaveTextContent("118");
    expect(blocked).toHaveTextContent("9% of requests");
    const approvals = screen.getByRole("group", { name: "Approvals open" });
    expect(approvals).toHaveTextContent("1");
    expect(approvals).toHaveTextContent("median decision 2 min 18 s");
    const spent = screen.getByRole("group", { name: "Spent" });
    expect(spent).toHaveTextContent("$0.8400");
    expect(spent).toHaveTextContent("42.3 s compute");
  });

  it("says when no approval has been decided and counts expired ones", () => {
    const { rerender } = render(<KpiRow metrics={fx.metrics({ approval_median_s: null })} />);
    expect(screen.getByRole("group", { name: "Approvals open" })).toHaveTextContent("none decided yet");
    rerender(<KpiRow metrics={fx.metrics({ approvals_expired: 2 })} />);
    expect(screen.getByRole("group", { name: "Approvals open" })).toHaveTextContent("2 expired");
  });

  it("keeps the private → external invariant calm at zero and loud above it", () => {
    const { rerender } = render(<KpiRow metrics={fx.metrics()} />);
    expect(screen.getByRole("group", { name: "Private → external" })).toHaveTextContent("0");
    expect(screen.queryByText("Breach")).not.toBeInTheDocument();
    rerender(<KpiRow metrics={fx.metrics({ private_to_external: 3 })} />);
    expect(screen.getByRole("group", { name: "Private → external" })).toHaveTextContent("Breach");
    expect(screen.getByText(/must stay at 0/)).toBeInTheDocument();
  });

  it("copes with an empty gateway", () => {
    const empty = fx.metrics({ requests: 0, by_decision: { ALLOW: 0, REDACT: 0, APPROVAL: 0, BLOCK: 0 }, open_approvals: 0,
      cost: { local_usd: 0, external_usd: 0, compute_s: 0 } });
    render(<KpiRow metrics={empty} />);
    expect(screen.getByRole("group", { name: "Blocked" })).toHaveTextContent("0% of requests");
    expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
  });
});

describe("PosturePanel", () => {
  it("draws the ring for the score with an accessible label", () => {
    const { container } = render(<PosturePanel posture={fx.posture({ score: 90, breakdown: [] })} />);
    expect(screen.getByRole("img", { name: "Security posture 90 out of 100" })).toBeInTheDocument();
    const val = container.querySelector(".val") as SVGCircleElement;
    expect(Number(val.getAttribute("stroke-dashoffset"))).toBeCloseTo(2 * Math.PI * 52 * 0.1, 3);
  });
  it("clamps nonsense scores and a zero maximum", () => {
    const { container, rerender } = render(<PosturePanel posture={fx.posture({ score: 250, max: 100 })} />);
    expect(Number((container.querySelector(".val") as Element).getAttribute("stroke-dashoffset"))).toBe(0);
    rerender(<PosturePanel posture={fx.posture({ score: 5, max: 0 })} />);
    expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
  });
});

describe("DeductionLine", () => {
  it("defines the score and names every deduction with its note and amount", () => {
    render(<DeductionLine posture={fx.posture({ breakdown: [
      { item: "dlp.redact_inflight", delta: -10, note: "removed" }, { item: "signature feed", delta: -10, note: "error" }] })} />);
    expect(screen.getByText(/not a risk score/)).toBeInTheDocument();
    expect(screen.getByText(/90 of 100/)).toBeInTheDocument();
    expect(screen.getByText(/14 of 15 controls active/)).toBeInTheDocument();
    expect(screen.getByText("dlp.redact_inflight")).toBeInTheDocument();
    expect(screen.getByText(/removed \(−10\)/)).toBeInTheDocument();
    expect(screen.getByText(/error \(−10\)/)).toBeInTheDocument();
    expect(screen.getByText(/score = 100/)).toBeInTheDocument();
  });
  it("says so when nothing is deducted, and works without a control count", () => {
    render(<DeductionLine posture={fx.posture({ breakdown: [], score: 100, controls_active: undefined, controls_total: undefined })} />);
    expect(screen.getByText(/No deductions\./)).toBeInTheDocument();
    expect(screen.queryByText(/controls active/)).not.toBeInTheDocument();
  });
});

describe("ThreatsPanel", () => {
  it("answers whether attacks arrive and what catches them", () => {
    render(<ThreatsPanel metrics={fx.metrics()} series={fx.timeseries()} />);
    expect(screen.getByRole("heading", { name: "Threats stopped" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Blocked: 54 in total, peak 12/ })).toBeInTheDocument();
    expect(screen.getByRole("listitem", { name: "sig.feed: 44 blocked" })).toHaveTextContent("LLM01:2026");
  });
  it("shows empty states instead of empty charts", () => {
    render(<ThreatsPanel metrics={fx.metrics({ top_blockers: [] })} series={null} />);
    expect(screen.getByText("No data in this window yet.")).toBeInTheDocument();
    expect(screen.getByText("Nothing has been blocked yet.")).toBeInTheDocument();
  });
  it("keeps only the five biggest blockers", () => {
    const many = Array.from({ length: 8 }, (_, i) => ({ rule: `r${i}`, owasp: [], blocked: 10 - i }));
    render(<ThreatsPanel metrics={fx.metrics({ top_blockers: many })} series={fx.timeseries()} />);
    expect(screen.getAllByRole("listitem", { name: /blocked$/ })).toHaveLength(5);
  });
});

describe("DataProtectionPanel", () => {
  it("shows, per data class, which model answered and that private data never went external", () => {
    render(<DataProtectionPanel metrics={fx.metrics()} />);
    expect(screen.getByRole("listitem", { name: "public: 320 Local model, 180 External model" })).toBeInTheDocument();
    expect(screen.getByRole("listitem", { name: "personal_data: 400 Local model, 0 External model" })).toHaveTextContent("0 to external");
    expect(screen.getByRole("listitem", { name: "bank_secret: 84 Local model, 0 External model" })).toHaveTextContent("0 to external");
    expect(screen.getByText("fields removed before they left the gateway.", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("61")).toBeInTheDocument();
  });
  it("flags private data that went to an external model", () => {
    const leaked = fx.metrics({ routing: [{ data_class: "personal_data", local: 10, external: 3 }] });
    render(<DataProtectionPanel metrics={leaked} />);
    expect(screen.getByText("3 to external")).toHaveClass("badge-red");
    expect(screen.queryByText("0 to external")).not.toBeInTheDocument();
  });
  it("orders classes from public to most sensitive and copes with no traffic", () => {
    const shuffled = fx.metrics({ routing: [
      { data_class: "bank_secret", local: 1, external: 0 }, { data_class: "public", local: 1, external: 0 }, { data_class: "personal_data", local: 1, external: 0 }] });
    const { container, rerender } = render(<DataProtectionPanel metrics={shuffled} />);
    expect([...container.querySelectorAll(".st-name")].map((e) => e.textContent)).toEqual(["public", "personal_data", "bank_secret"]);
    rerender(<DataProtectionPanel metrics={fx.metrics({ routing: [{ data_class: "public", local: 0, external: 0 }], redacted_fields: undefined })} />);
    expect(screen.getByText("No traffic yet.")).toBeInTheDocument();
  });
});

describe("OwaspPanel", () => {
  it("shows the edition, counts per status, the passing-tests note and a tile per category", () => {
    render(<OwaspPanel owasp={fx.owasp()} />);
    expect(screen.getByRole("heading", { name: "OWASP LLM Top 10 (2026) coverage" })).toBeInTheDocument();
    expect(screen.getByText(/1 enforced, 1 monitor only, 1 uncovered/)).toBeInTheDocument();
    expect(screen.getByText(/10\/10 categories have a passing test/)).toBeInTheDocument();
    const enforced = screen.getByRole("group", { name: "LLM01:2026" });
    expect(enforced).toHaveTextContent("41 blocked");
    expect(enforced.querySelector(".cov")).not.toHaveClass("mon", "unc");
    const monitor = screen.getByRole("group", { name: "LLM02:2026" });
    expect(monitor.querySelector(".cov")).toHaveClass("mon");
    expect(monitor).toHaveTextContent("monitor only");
    const gap = screen.getByRole("group", { name: "LLM07:2026" });
    expect(gap.querySelector(".cov")).toHaveClass("unc");
    expect(gap).toHaveTextContent("no grounding control");
  });
  it("leaves out the uncovered count when everything is covered", () => {
    render(<OwaspPanel owasp={fx.owasp({ categories: [fx.owasp().categories[0]] })} />);
    expect(screen.getByText(/1 enforced, 0 monitor only\./)).toBeInTheDocument();
    expect(screen.queryByText(/uncovered/)).not.toBeInTheDocument();
  });
});
