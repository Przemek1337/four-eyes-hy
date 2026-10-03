import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../api/client";
import { fx } from "../test/fixtures";
import { ManagementView } from "./ManagementView";

vi.mock("../api/client", () => ({
  api: {
    metrics: vi.fn(), posture: vi.fn(), owasp: vi.fn(), timeseries: vi.fn(), controls: vi.fn(), policy: vi.fn(),
    signatures: vi.fn(), budgets: vi.fn(), tests: vi.fn(),
  },
}));

beforeEach(() => {
  vi.mocked(api.metrics).mockResolvedValue(fx.metrics());
  vi.mocked(api.posture).mockResolvedValue(fx.posture({ score: 100, breakdown: [] }));
  vi.mocked(api.owasp).mockResolvedValue(fx.owasp());
  vi.mocked(api.timeseries).mockResolvedValue(fx.timeseries());
  vi.mocked(api.controls).mockResolvedValue({ controls: fx.controls().map((c) => ({ ...c, status: "active" as const })), last_diff: [] });
  vi.mocked(api.policy).mockResolvedValue(fx.policy());
  vi.mocked(api.signatures).mockResolvedValue(fx.signatures());
  vi.mocked(api.budgets).mockResolvedValue(fx.budgets());
  vi.mocked(api.tests).mockResolvedValue(fx.tests());
});

const open = async (name: string) => userEvent.click(await screen.findByRole("tab", { name: new RegExp(`^${name}`) }));

describe("ManagementView overview", () => {
  it("opens on the overview: posture, the figures and one sentence per section, but no charts", async () => {
    render(<ManagementView />);
    expect(await screen.findByRole("img", { name: "Security posture 100 out of 100" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Requests" })).toHaveTextContent("1,284");
    expect(screen.getByText(/Policy v4\./)).toBeInTheDocument();
    expect(await screen.findByRole("list", { name: "Sections at a glance" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("heading", { name: "Threats stopped" })).not.toBeInTheDocument(); // one section at a time
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("summarises each section in a sentence and opens it on click", async () => {
    render(<ManagementView />);
    const list = await screen.findByRole("list", { name: "Sections at a glance" });
    await screen.findByText(/142 of 142 tests pass/);
    expect(within(list).getByText(/118 blocked \(9% of requests\)/)).toBeInTheDocument();
    expect(within(list).getByText(/No private data reached an external model/)).toBeInTheDocument();
    expect(within(list).getByText(/3 of 3 controls active/)).toBeInTheDocument();
    expect(within(list).getByText(/142 of 142 tests pass\. Missed attacks 0, false blocks 0/)).toBeInTheDocument();
    await userEvent.click(within(list).getByRole("button", { name: /Speed/ }));
    expect(screen.getByRole("tab", { name: "Speed" })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("region", { name: "Gateway overhead" })).toBeInTheDocument();
  });

  it("flags the sections that need a person, in the list and on the tabs", async () => {
    vi.mocked(api.budgets).mockResolvedValue(fx.budgets()); // playground near its limit, treasury at it
    vi.mocked(api.controls).mockResolvedValue({ controls: fx.controls(), last_diff: [] }); // one removed
    render(<ManagementView />);
    const list = await screen.findByRole("list", { name: "Sections at a glance" });
    await screen.findByText(/at its limit/);
    expect(within(list).getAllByText("Needs attention").length).toBeGreaterThanOrEqual(2);
    expect(within(screen.getByRole("tab", { name: /Cost/ })).getByRole("img", { name: "needs attention" })).toBeInTheDocument();
    expect(within(screen.getByRole("tab", { name: /Policy/ })).getByRole("img", { name: "needs attention" })).toBeInTheDocument();
    expect(within(screen.getByRole("tab", { name: /Speed/ })).queryByRole("img")).not.toBeInTheDocument();
  });
});

describe("ManagementView sections", () => {
  it("shows threats, data, cost, speed and proof one at a time", async () => {
    render(<ManagementView />);
    await open("Threats");
    expect(await screen.findByRole("heading", { name: "Threats stopped" })).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: /Blocked: 54 in total/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Data protection" })).not.toBeInTheDocument();
    await open("Data");
    expect(await screen.findByRole("heading", { name: "Data protection" })).toBeInTheDocument();
    await open("Cost");
    expect(await screen.findByRole("region", { name: "Budgets and cost" })).toBeInTheDocument();
    await open("Proof");
    expect(await screen.findByRole("region", { name: "Test suite" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: /OWASP LLM Top 10/ })).toBeInTheDocument();
  });

  it("shows policy health: controls, what the policy is set to, known attacks and history", async () => {
    render(<ManagementView />);
    await open("Policy");
    expect(await screen.findByRole("region", { name: "Controls" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Policy at a glance" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Known attacks blocked" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Policy and feed" })).toBeInTheDocument();
  });

  it("keeps working when one section cannot be loaded", async () => {
    vi.mocked(api.budgets).mockRejectedValue(new Error("no budgets"));
    render(<ManagementView />);
    await screen.findByRole("img", { name: /Security posture/ });
    await open("Cost");
    expect(await screen.findByRole("alert")).toHaveTextContent("no budgets");
    await open("Speed");
    expect(await screen.findByRole("region", { name: "Gateway overhead" })).toBeInTheDocument();
  });

  it("still shows the figures when the time series cannot be loaded", async () => {
    vi.mocked(api.timeseries).mockRejectedValue(new Error("no series"));
    render(<ManagementView />);
    expect(await screen.findByRole("group", { name: "Requests" })).toBeInTheDocument();
    await open("Threats");
    expect(await screen.findByText("No data in this window yet.")).toBeInTheDocument();
  });
});

describe("ManagementView alerts", () => {
  it("stay visible on every tab: a control removed from the policy", async () => {
    vi.mocked(api.controls).mockResolvedValue({ controls: fx.controls(), last_diff: ["- controls.dlp.redact_inflight"] });
    render(<ManagementView />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("dlp.redact_inflight was removed from the policy");
    await open("Speed");
    expect(screen.getByRole("alert")).toHaveTextContent("dlp.redact_inflight was removed");
  });

  it("includes the posture drop when the posture endpoint reports one", async () => {
    vi.mocked(api.posture).mockResolvedValue(fx.posture());
    render(<ManagementView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Posture dropped by 10");
  });

  it("raises an alert when private data reached an external model", async () => {
    vi.mocked(api.metrics).mockResolvedValue(fx.metrics({ private_to_external: 2 }));
    render(<ManagementView />);
    expect(await screen.findByText("Private data reached an external model.")).toBeInTheDocument();
  });

  it("explains a failed load instead of crashing", async () => {
    vi.mocked(api.metrics).mockRejectedValue(new Error("backend down"));
    render(<ManagementView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("backend down");
    const list = screen.getByRole("list", { name: "Sections at a glance" }); // still there: the other sections do not depend on metrics
    expect(await within(list).findByText(/3 of 3 controls active/)).toBeInTheDocument();
    expect(within(list).getAllByText("Not available right now.").length).toBeGreaterThanOrEqual(1);
  });
});
