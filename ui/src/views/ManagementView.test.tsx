import { render, screen } from "@testing-library/react";
import { api } from "../api/client";
import { fx } from "../test/fixtures";
import { ManagementView } from "./ManagementView";

vi.mock("../api/client", () => ({
  api: { metrics: vi.fn(), posture: vi.fn(), owasp: vi.fn(), timeseries: vi.fn(), controls: vi.fn(), policy: vi.fn(), signatures: vi.fn() },
}));

beforeEach(() => {
  vi.mocked(api.metrics).mockResolvedValue(fx.metrics());
  vi.mocked(api.posture).mockResolvedValue(fx.posture({ score: 100, breakdown: [] }));
  vi.mocked(api.owasp).mockResolvedValue(fx.owasp());
  vi.mocked(api.timeseries).mockResolvedValue(fx.timeseries());
  vi.mocked(api.controls).mockResolvedValue({ controls: fx.controls().map((c) => ({ ...c, status: "active" as const })), last_diff: [] });
  vi.mocked(api.policy).mockResolvedValue(fx.policy());
  vi.mocked(api.signatures).mockResolvedValue(fx.signatures());
});

describe("ManagementView", () => {
  it("shows the posture, the figures and OWASP coverage once loaded", async () => {
    render(<ManagementView />);
    expect(await screen.findByRole("img", { name: "Security posture 100 out of 100" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Requests" })).toHaveTextContent("1,284");
    expect(await screen.findByRole("heading", { name: /OWASP LLM Top 10/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Threats stopped" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Data protection" })).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: /Blocked: 54 in total/ })).toBeInTheDocument();
    expect(screen.getByText(/Policy v4\./)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows policy health: controls, what the policy is set to, known attacks and history", async () => {
    render(<ManagementView />);
    expect(await screen.findByRole("region", { name: "Controls" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Policy at a glance" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Known attacks blocked" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Policy and feed" })).toBeInTheDocument();
  });

  it("warns from the controls table even when the posture endpoint is silent about it", async () => {
    vi.mocked(api.controls).mockResolvedValue({ controls: fx.controls(), last_diff: ["- controls.dlp.redact_inflight"] });
    render(<ManagementView />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("dlp.redact_inflight was removed from the policy");
    expect(alert).not.toHaveTextContent("Posture dropped"); // posture reports no deduction in this case
  });

  it("warns when a control was removed from the policy", async () => {
    vi.mocked(api.posture).mockResolvedValue(fx.posture());
    render(<ManagementView />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("dlp.redact_inflight was removed from the policy");
    expect(alert).toHaveTextContent("Posture dropped by 10");
  });

  it("raises an alert when private data reached an external model", async () => {
    vi.mocked(api.metrics).mockResolvedValue(fx.metrics({ private_to_external: 2 }));
    render(<ManagementView />);
    expect(await screen.findByText("Private data reached an external model.")).toBeInTheDocument();
  });

  it("still shows the figures when the time series cannot be loaded", async () => {
    vi.mocked(api.timeseries).mockRejectedValue(new Error("no series"));
    render(<ManagementView />);
    expect(await screen.findByRole("group", { name: "Blocked" })).toBeInTheDocument();
    expect(screen.getByText("No data in this window yet.")).toBeInTheDocument();
  });

  it("explains a failed load on every panel instead of crashing", async () => {
    vi.mocked(api.metrics).mockRejectedValue(new Error("backend down"));
    vi.mocked(api.owasp).mockRejectedValue(new Error("backend down"));
    render(<ManagementView />);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.length).toBeGreaterThanOrEqual(2);
    expect(alerts[0]).toHaveTextContent("backend down");
  });
});
