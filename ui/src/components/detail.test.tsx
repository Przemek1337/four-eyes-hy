import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../api/client";
import { fx } from "../test/fixtures";
import { buildTimeline, taintedFrom } from "../timeline";
import { FlowMap } from "./FlowMap";
import { SessionDetail } from "./SessionDetail";
import { SessionHeader } from "./SessionHeader";
import { Timeline } from "./Timeline";
import { WhyBlocked } from "./WhyBlocked";

vi.mock("../api/client", () => ({ api: { session: vi.fn(), decide: vi.fn() } }));

const stopped = fx.decision({
  decision_id: "d3", resource: "entities_submit", decision: "BLOCK", rule: "sig.feed", code: "KNOWN_ATTACK",
  reason: "prompt matches known jailbreak pattern SIG-PRM-001", layer: "det", owasp: ["LLM01:2026", "ASI01"],
  signature_id: "SIG-PRM-001", policy_version: "v4", labels: ["untrusted"],
  detail: { reference: "Classic jailbreak phrasing", evidence: "skip sanctions screening" }, injection_score: 0.95,
});

describe("SessionHeader", () => {
  const base = { ...fx.session(), scope: { client_id: "C1" }, task: "KYC for Nordwind" };
  it("shows the headline, where the session turned untrusted and what was stopped or is waiting", () => {
    render(<SessionHeader session={base} headline="kyc-agent tried entities_submit and FourEyes stopped it" taintedFrom={2} />);
    expect(screen.getByRole("heading", { name: /FourEyes stopped it/ })).toBeInTheDocument();
    expect(screen.getByText("untrusted since step 2")).toBeInTheDocument();
    expect(screen.getByText("1 action stopped")).toBeInTheDocument();
    expect(screen.getByText("1 waiting")).toBeInTheDocument();
    expect(screen.getByText("bank_secret")).toBeInTheDocument();
    expect(screen.getByText("a41f")).toBeInTheDocument();
    expect(screen.getByText("Nowak Logistics")).toBeInTheDocument();
    expect(screen.getByText(/KYC for Nordwind/)).toBeInTheDocument();
  });
  it("shows a clean session without warnings", () => {
    const clean = { ...fx.session({ labels: [], status: "clean", blocked_count: 0, pending_approvals: 0 }), scope: {}, task: null };
    render(<SessionHeader session={clean} headline="kyc-agent ran 3 steps and nothing was stopped" taintedFrom={null} />);
    expect(screen.queryByText(/untrusted since/)).not.toBeInTheDocument();
    expect(screen.queryByText(/stopped/)).toBeInTheDocument(); // only inside the headline
    expect(screen.queryByText(/waiting/)).not.toBeInTheDocument();
  });
});

describe("Timeline", () => {
  const items = buildTimeline([
    fx.decision({ decision_id: "d1" }),
    { event: "label.added", ts: "t", session_id: "a41f", label: "high_risk", reason: "x" },
    stopped,
    fx.decision({ decision_id: "d4", resource: "send_email", decision: "APPROVAL", labels: ["untrusted"] }),
  ]);

  it("renders a toggle button per step and a small row per note, with state classes", () => {
    render(<Timeline items={items} expanded={new Set(["d3"])} onToggle={() => {}} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(3);
    expect(buttons[1]).toHaveAttribute("aria-expanded", "true");
    expect(buttons[0]).toHaveAttribute("aria-expanded", "false");
    expect(buttons[1].closest("li")).toHaveClass("stop", "open");
    expect(buttons[2].closest("li")).toHaveClass("hold");
    expect(screen.getByText("high_risk")).toBeInTheDocument();
  });
  it("puts every step from the first untrusted one, and the notes between them, in one zone", () => {
    const { container } = render(<Timeline items={items} expanded={new Set()} onToggle={() => {}} />);
    expect(screen.getAllByText("Session is untrusted from here")).toHaveLength(1);
    const zone = container.querySelector(".tl-zone") as HTMLElement;
    expect(within(zone).getByRole("button", { name: /entities_submit/ })).toBeInTheDocument();
    expect(within(zone).getByRole("button", { name: /send_email/ })).toBeInTheDocument();
    expect(zone.textContent).not.toContain("Model call"); // the clean first step stays outside
    const firstButton = screen.getAllByRole("button")[0];
    expect(zone.contains(firstButton)).toBe(false);
  });
  it("has no zone when nothing is untrusted", () => {
    const { container } = render(<Timeline items={buildTimeline([fx.decision({ decision_id: "ok" })])} expanded={new Set()} onToggle={() => {}} />);
    expect(container.querySelector(".tl-zone")).toBeNull();
    expect(screen.queryByText("Session is untrusted from here")).not.toBeInTheDocument();
  });
  it("labels the toggle by state and reports which step was toggled", async () => {
    const onToggle = vi.fn();
    render(<Timeline items={items} expanded={new Set(["d3"])} onToggle={onToggle} />);
    expect(screen.getAllByText("Hide details")).toHaveLength(1);
    expect(screen.getAllByText("Show details")).toHaveLength(2);
    await userEvent.click(screen.getAllByRole("button")[0]);
    expect(onToggle).toHaveBeenCalledWith("d1");
  });
  it("shows detail under every expanded step and under no other", () => {
    render(<Timeline items={items} expanded={new Set(["d1", "d3"])} onToggle={() => {}} renderDetail={(it) => <p>detail for {it.key}</p>} />);
    expect(screen.getByText("detail for d1")).toBeInTheDocument();
    expect(screen.getByText("detail for d3")).toBeInTheDocument();
    expect(screen.queryByText("detail for d4")).not.toBeInTheDocument();
  });
  it("shows an empty state", () => {
    render(<Timeline items={[]} expanded={new Set()} onToggle={() => {}} />);
    expect(screen.getByText("No steps recorded yet.")).toBeInTheDocument();
  });
  it("renders hostile and huge text as plain text", () => {
    const hostile = fx.decision({ decision_id: "h", decision: "BLOCK", rule: "<script>alert(1)</script>", code: "x".repeat(10_000) });
    const { container } = render(<Timeline items={buildTimeline([hostile])} expanded={new Set()} onToggle={() => {}} />);
    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).toContain("<script>alert(1)</script>");
  });
  it("knows where the untrusted band starts", () => {
    expect(taintedFrom(items)).toBe(2);
  });
});

describe("WhyBlocked", () => {
  it("shows rule, layer, OWASP tags with year, signature, reference, evidence and score", () => {
    render(<WhyBlocked event={stopped} />);
    const panel = screen.getByRole("region", { name: "Why this decision" });
    expect(within(panel).getByText("BLOCK")).toBeInTheDocument();
    expect(within(panel).getByText("sig.feed")).toBeInTheDocument();
    expect(within(panel).getByText("Deterministic")).toBeInTheDocument();
    expect(within(panel).getByText("LLM01:2026")).toBeInTheDocument();
    expect(within(panel).getByText("ASI01")).toBeInTheDocument();
    expect(within(panel).getByText("SIG-PRM-001")).toBeInTheDocument();
    expect(within(panel).getByText("Classic jailbreak phrasing")).toBeInTheDocument();
    expect(within(panel).getByText("skip sanctions screening")).toBeInTheDocument();
    expect(within(panel).getByText("0.95")).toBeInTheDocument();
    expect(within(panel).getByText(/policy v4/)).toBeInTheDocument();
  });
  it("prefers the contract fields evidence and reference when the backend sends them", () => {
    const ev = fx.decision({ decision: "BLOCK", signature_id: "SIG-PKL-001", reference: "Malicious pickle models (2024)", evidence: "os.system", detail: {} });
    render(<WhyBlocked event={ev} />);
    expect(screen.getByText("Malicious pickle models (2024)")).toBeInTheDocument();
    expect(screen.getByText("os.system")).toBeInTheDocument();
  });
  it("shows the AI judge's view from the approval and tolerates a missing one", () => {
    const held = fx.decision({ decision: "APPROVAL", rule: "flow.untrusted", layer: "ai", detail: {} });
    const { rerender } = render(<WhyBlocked event={held} approval={fx.approval()} />);
    expect(screen.getByText("AI (semantic)")).toBeInTheDocument();
    expect(screen.getByText(/0\.91/)).toBeInTheDocument();
    rerender(<WhyBlocked event={held} approval={fx.approval({ judge: null })} />);
    expect(screen.getByText("AI judge")).toBeInTheDocument();
    expect(screen.getByText("not run")).toBeInTheDocument();
  });
  it("asks for a selection when there is none and escapes hostile evidence", () => {
    const { rerender, container } = render(<WhyBlocked event={null} />);
    expect(screen.getByText("Select a step to see the rule behind it.")).toBeInTheDocument();
    rerender(<WhyBlocked event={fx.decision({ decision: "BLOCK", detail: { evidence: "<img src=x onerror=alert(1)>" } })} />);
    expect(container.querySelector("img")).toBeNull();
  });
});

describe("FlowMap", () => {
  it("shows sources, the agent with its labels and where each destination ended up", () => {
    render(<FlowMap flow={fx.flow()} />);
    const map = screen.getByRole("region", { name: "Where the data went" });
    expect(within(map).getByText("client_upload.pdf")).toBeInTheDocument();
    expect(within(map).getByText("Labels added at step 2")).toBeInTheDocument();
    expect(within(map).getByText("unavailable for this session")).toBeInTheDocument();
    expect(within(map).getByText("blocked")).toBeInTheDocument();
    expect(within(map).getByText("held for approval")).toBeInTheDocument();
    expect(within(map).getByText("passed")).toBeInTheDocument();
  });
});

describe("SessionDetail", () => {
  const detail = {
    session: { ...fx.session(), scope: { client_id: "C1" }, task: "KYC for Nordwind" },
    events: [
      fx.decision({ decision_id: "d1", kind: "model", resource: "qwen2.5:7b", route: { allowed: ["local"], chosen: "local", model: "qwen2.5:7b", router: "default", rerouted_from: null, fallback: false } }),
      fx.decision({ decision_id: "d2", resource: "entities_documents_read", labels: ["untrusted", "high_risk"] }),
      stopped,
    ],
    approvals: [],
  };

  it("opens the stopped steps by default and lets the user open and close any step", async () => {
    vi.mocked(api.session).mockResolvedValue(detail);
    render(<SessionDetail sessionId="a41f" />);
    const why = await screen.findByRole("region", { name: "Why this decision" });
    expect(within(why).getByText("KNOWN_ATTACK")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /tried entities_submit and FourEyes stopped it/ })).toBeInTheDocument();
    expect(screen.getAllByRole("region", { name: "Why this decision" })).toHaveLength(1); // only the stopped step

    const read = screen.getByRole("button", { name: /entities_documents_read/ });
    expect(read).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(read);
    expect(read).toHaveAttribute("aria-expanded", "true");
    expect(screen.getAllByRole("region", { name: "Why this decision" })).toHaveLength(2); // both open at once
    await userEvent.click(read);
    expect(screen.getAllByRole("region", { name: "Why this decision" })).toHaveLength(1);
  });

  it("expands and collapses every step at once", async () => {
    vi.mocked(api.session).mockResolvedValue(detail);
    render(<SessionDetail sessionId="a41f" />);
    await screen.findByRole("region", { name: "Why this decision" });
    await userEvent.click(screen.getByRole("button", { name: "Expand all" }));
    expect(screen.getAllByRole("region", { name: "Why this decision" })).toHaveLength(3);
    await userEvent.click(screen.getByRole("button", { name: "Collapse all" }));
    expect(screen.queryByRole("region", { name: "Why this decision" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Expand all" })).toBeInTheDocument();
  });

  it("shows the data-flow map only when the backend provides it", async () => {
    vi.mocked(api.session).mockResolvedValue(detail);
    const { unmount } = render(<SessionDetail sessionId="a41f" />);
    await screen.findByRole("region", { name: "Why this decision" });
    expect(screen.queryByRole("region", { name: "Where the data went" })).not.toBeInTheDocument();
    unmount();
    vi.mocked(api.session).mockResolvedValue({ ...detail, flow: fx.flow() });
    render(<SessionDetail sessionId="a41f" />);
    expect(await screen.findByRole("region", { name: "Where the data went" })).toBeInTheDocument();
  });

  it("shows an error when the session cannot be loaded", async () => {
    vi.mocked(api.session).mockRejectedValue(new Error("unknown session"));
    render(<SessionDetail sessionId="nope" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("unknown session");
  });
});
