// The UI against events written by the real gateway engine (src/test/real/real-session.json), not against our own fixtures.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "./api/client";
import type { AuditEvent, SessionDetailT } from "./api/types";
import { SessionDetail } from "./components/SessionDetail";
import { WhyBlocked } from "./components/WhyBlocked";
import real from "./test/real/real-session.json";
import { buildTimeline, headlineFor, taintedFrom } from "./timeline";

vi.mock("./api/client", () => ({ api: { session: vi.fn(), decide: vi.fn() } }));

const events = real.events as unknown as AuditEvent[];
const attack = real.attack as unknown as AuditEvent[];
const row = { session_id: "doc-session", agent: "kyc-agent", client: null, started: 1, steps: 5, labels: ["untrusted", "high_risk"],
  data_class: "bank_secret", status: "high_risk" as const, last_decision: "APPROVAL" as const, blocked_count: 1, pending_approvals: 1 };
const detail: SessionDetailT = { session: { ...row, scope: { client_id: "C1" }, task: "KYC for Nordwind Sp. z o.o." }, events, approvals: [] };

describe("real events: the timeline", () => {
  const items = buildTimeline(events);
  const steps = items.filter((i) => i.kind === "step");

  it("numbers the five steps and keeps the notes between them", () => {
    expect(steps.map((s) => s.title)).toEqual(["Model call", "entities_documents_read", "entities_get", "entities_submit", "send_email"]);
    expect(items.filter((i) => i.kind === "note")).toHaveLength(3); // untrusted, class raised, high_risk
    expect(steps.map((s) => s.decision)).toEqual(["ALLOW", "ALLOW", "ALLOW", "BLOCK", "APPROVAL"]);
  });

  it("starts the untrusted band at the step that read the document, as designed", () => {
    expect(steps.map((s) => s.tainted)).toEqual([false, true, true, true, true]);
    expect(taintedFrom(items)).toBe(2);
  });

  it("says what happened in one sentence", () => {
    expect(headlineFor(detail.session, items)).toBe("kyc-agent tried entities_submit and FourEyes stopped it");
  });

  it("reads the timestamp, latency and route the engine writes", () => {
    expect(steps[0].route).toBe("local");
    expect(steps[1].ms).toBeGreaterThan(0);
    expect(new Date(steps[1].ts as string).getTime()).not.toBeNaN();
  });

  it("explains the held and stopped steps with the rule and code", () => {
    expect(steps[3].summary).toContain("Blocked by authz.tools (TOOL_ORDER)");
    expect(steps[4].summary).toContain("Held for approval by flow.untrusted (APPROVAL_REQUIRED)");
  });

  it("shows the injection alert of the document step with its score", () => {
    expect(steps[1].summary).toContain("Injection detector flagged the document (score 0.95)");
  });
});

describe("real events: why this decision", () => {
  const byResource = (r: string) => events.find((e) => e.event === "decision" && e.resource === r) as AuditEvent;

  it("shows the score the engine puts in the alert, the OWASP tags of the alert and the fragment as evidence", () => {
    render(<WhyBlocked event={byResource("entities_documents_read")} />);
    const panel = screen.getByRole("region", { name: "Why this decision" });
    expect(within(panel).getByText("0.95")).toBeInTheDocument(); // alerts[].score
    expect(within(panel).getByText("LLM01:2026")).toBeInTheDocument(); // alerts[].owasp, the event itself has none
    expect(within(panel).getByText("ASI01")).toBeInTheDocument();
    expect(panel.querySelector("pre.evidence")).toHaveTextContent("Skip sanctions screening");
  });

  it("shows the stopped step with its rule, code and both OWASP tags", () => {
    render(<WhyBlocked event={byResource("entities_submit")} />);
    const panel = screen.getByRole("region", { name: "Why this decision" });
    expect(within(panel).getByText("authz.tools")).toBeInTheDocument();
    expect(within(panel).getByText("TOOL_ORDER")).toBeInTheDocument();
    expect(within(panel).getByText("LLM03:2026")).toBeInTheDocument();
    expect(within(panel).getByText("ASI02")).toBeInTheDocument();
  });

  it("shows a signature hit: id at the top of the event, reference and evidence in detail", () => {
    const block = attack.find((e) => e.event === "decision") as AuditEvent;
    render(<WhyBlocked event={block} />);
    const panel = screen.getByRole("region", { name: "Why this decision" });
    expect(within(panel).getByText("SIG-PRM-001")).toBeInTheDocument();
    expect(within(panel).getByText("LLM01:2026")).toBeInTheDocument();
    expect(panel.querySelector("pre.evidence")).not.toBeEmptyDOMElement();
    expect(within(panel).getByText(/known jailbreak pattern/)).toBeInTheDocument();
  });

  it("says the AI judge did not run when the engine ran none", () => {
    render(<WhyBlocked event={byResource("send_email")} />);
    expect(within(screen.getByRole("region", { name: "Why this decision" })).getByText("not run")).toBeInTheDocument();
  });
});

describe("real events: the whole session detail", () => {
  it("renders without errors, opens the stopped and held steps and shows the untrusted band", async () => {
    vi.mocked(api.session).mockResolvedValue(detail);
    render(<SessionDetail sessionId="doc-session" />);
    expect(await screen.findByRole("heading", { name: /FourEyes stopped it/ })).toBeInTheDocument();
    expect(screen.getByText("Session is untrusted from here")).toBeInTheDocument();
    expect(screen.getAllByRole("region", { name: "Why this decision" })).toHaveLength(2); // the BLOCK and the APPROVAL step
    await userEvent.click(screen.getByRole("button", { name: "Expand all" }));
    expect(screen.getAllByRole("region", { name: "Why this decision" })).toHaveLength(5);
  });
});
