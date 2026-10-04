import { render, screen, within } from "@testing-library/react";
import { fx } from "../test/fixtures";
import { ControlsPanel } from "./ControlsPanel";
import { KnownAttacks } from "./KnownAttacks";
import { PolicyGlance } from "./PolicyGlance";
import { PolicyPanel } from "./PolicyPanel";

describe("ControlsPanel", () => {
  it("shows each control with type, setting, status, OWASP tags, hits and p95", () => {
    render(<ControlsPanel controls={fx.controls()} lastDiff={[]} />);
    const rows = screen.getAllByRole("row");
    expect(rows).toHaveLength(4); // header + 3 controls
    const ai = rows.find((r) => within(r).queryByText("sem.prompt_injection"))!;
    expect(within(ai).getByText("AI")).toBeInTheDocument();
    expect(within(ai).getByText("block above 0.8")).toBeInTheDocument(); // the human-readable setting
    expect(within(ai).getByText("Monitor only")).toBeInTheDocument();
    expect(within(ai).getByText("LLM01:2026")).toBeInTheDocument();
    expect(within(ai).getByText("7")).toBeInTheDocument();
    expect(within(ai).getByText("24.0 ms")).toBeInTheDocument();
    const rule = rows.find((r) => within(r).queryByText("auth.agent_key"))!;
    expect(within(rule).getByText("Rule")).toBeInTheDocument();
    expect(within(rule).getByText("Active")).toBeInTheDocument();
  });

  it("marks a removed control: struck id, Removed pill, no figures", () => {
    render(<ControlsPanel controls={fx.controls()} lastDiff={[]} />);
    const row = screen.getAllByRole("row").find((r) => within(r).queryByText("dlp.redact_inflight"))!;
    expect(within(row).getByText("dlp.redact_inflight")).toHaveClass("struck");
    expect(within(row).getByText("Removed")).toHaveClass("badge-red");
    expect(within(row).getAllByText("–")).toHaveLength(2); // no hits or latency for something that does not run
    expect(row).toHaveClass("removed");
  });

  it("falls back to the mode and compact parameters when the backend sends no setting", () => {
    const c = fx.controls().map((x) => ({ ...x, setting: undefined }));
    render(<ControlsPanel controls={c} lastDiff={[]} />);
    expect(screen.getByText(/block_above/)).toBeInTheDocument();
    expect(screen.getAllByText("enforce").length).toBeGreaterThan(0);
  });

  it("shows the last policy change as a diff, and says when there is none", () => {
    const { rerender } = render(<ControlsPanel controls={fx.controls()} lastDiff={["~ profile: 'strict' -> 'relaxed'", "- controls.dlp.redact_inflight"]} />);
    expect(screen.getByText(/~ profile: 'strict' -> 'relaxed'/)).toBeInTheDocument();
    expect(document.querySelector("pre.diff")).toHaveTextContent("- controls.dlp.redact_inflight");
    rerender(<ControlsPanel controls={fx.controls()} lastDiff={[]} />);
    expect(screen.getByText("No changes since the gateway started.")).toBeInTheDocument();
  });

  it("truncates huge parameter blobs and renders hostile text as text", () => {
    const big = fx.controls().map((x) => ({ ...x, setting: undefined }));
    big[1] = { ...big[1], params: { blob: "x".repeat(5000) } };
    big[0] = { ...big[0], description: "<img src=x onerror=alert(1)>" };
    const { container } = render(<ControlsPanel controls={big} lastDiff={[]} />);
    expect(screen.getByText(/^\{"blob":"x+…$/)).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
  });

  it("names the decision model of an AI control and flags it when it is down", () => {
    const c = fx.controls().map((row) => row.id === "sem.prompt_injection"
      ? { ...row, model: "granite_guardian", model_status: "down" as const } : row);
    render(<ControlsPanel controls={c} lastDiff={[]} />);
    const row = screen.getAllByRole("row").find((r) => within(r).queryByText("sem.prompt_injection"))!;
    expect(within(row).getByText("granite_guardian")).toBeInTheDocument();
    expect(within(row).getByText("Down")).toHaveClass("badge-red");
    expect(within(row).getByText("AI")).toBeInTheDocument();
  });
});

describe("PolicyGlance", () => {
  it("lists what the policy blocks or redacts, which models are allowed and the budget rules", () => {
    render(<PolicyGlance summary={fx.policy().summary!} />);
    const region = screen.getByRole("region", { name: "Policy at a glance" });
    expect(within(region).getByText("block above 0.8, log above 0.5")).toBeInTheDocument();
    expect(within(region).getByText("public data only")).toBeInTheDocument();
    expect(within(region).getByText("$2.00 and 600 compute s a day")).toBeInTheDocument();
    expect(within(region).getByRole("heading", { name: "Allowed models" })).toBeInTheDocument();
  });
});

describe("KnownAttacks", () => {
  it("shows each signature type with what it matches, the reference and how many it stopped", () => {
    render(<KnownAttacks signatures={fx.signatures()} />);
    const pickle = screen.getAllByRole("row").find((r) => within(r).queryByText("pickle_opcode"))!;
    expect(within(pickle).getByText(/SIG-PKL-001 · Malicious pickle models/)).toBeInTheDocument();
    expect(within(pickle).getByText("3")).toBeInTheDocument();
    const url = screen.getAllByRole("row").find((r) => within(r).queryByText("url_pattern"))!;
    expect(within(url).getByText("EchoLeak, CVE-2025-32711")).toBeInTheDocument(); // no id invented when there is none
    expect(within(url).queryByText(/SIG-/)).not.toBeInTheDocument();
  });
  it("says so when no known attack has been seen", () => {
    render(<KnownAttacks signatures={{ ...fx.signatures(), hits: [] }} />);
    expect(screen.getByText("No known attack has been seen yet.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

describe("PolicyPanel", () => {
  it("shows the version, history with diffs and a healthy feed", () => {
    render(<PolicyPanel policy={fx.policy()} />);
    const panel = screen.getByRole("region", { name: "Policy and feed" });
    expect(within(panel).getByText(/Profile strict/)).toBeInTheDocument();
    expect(within(panel).getByText("~ profile: 'strict' -> 'relaxed'")).toBeInTheDocument();
    expect(within(panel).getByText("policy.rejected")).toHaveClass("badge-red");
    expect(within(panel).getByText("unknown control 'made.up'")).toBeInTheDocument();
    expect(within(panel).getByText("2026-10-03.1")).toBeInTheDocument();
    expect(within(panel).getByText("7 signatures")).toBeInTheDocument();
    expect(within(panel).getByText("None")).toBeInTheDocument();
    expect(within(panel).queryByRole("alert")).not.toBeInTheDocument();
  });

  it("flags a rejected policy and a failing feed as alerts", () => {
    render(<PolicyPanel policy={fx.policy({ error: "auth.agent_key is a baseline control and cannot be removed",
      feed: { version: "2026-10-03.1", count: 7, last_reload: 1, error: "feed rejected: unknown signature type", source: "f" } })} />);
    const alerts = screen.getAllByRole("alert");
    expect(alerts[0]).toHaveTextContent("baseline control");
    expect(alerts[0]).toHaveTextContent("The previous policy is still running");
    expect(alerts[1]).toHaveTextContent("feed rejected");
  });

  it("caps long diffs, and handles an empty history and a feed that never loaded", () => {
    const long = fx.policy({ history: [{ version: "v5", ts: 1, event: "policy.reloaded", diff: Array.from({ length: 8 }, (_, i) => `+ line ${i}`) }] });
    const { rerender } = render(<PolicyPanel policy={long} />);
    expect(screen.getByText("+3 more")).toBeInTheDocument();
    rerender(<PolicyPanel policy={fx.policy({ history: [], feed: { version: null, count: 0, last_reload: null, error: null, source: null } })} />);
    expect(screen.getByText("No changes recorded yet.")).toBeInTheDocument();
    expect(screen.getByText("not loaded")).toBeInTheDocument();
  });
});
