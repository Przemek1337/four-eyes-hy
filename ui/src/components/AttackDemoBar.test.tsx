import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, ApiError } from "../api/client";
import type { AttackStatusT } from "../api/types";
import { AttackDemoBar } from "./AttackDemoBar";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return { ...actual, api: { attackStatus: vi.fn(), startAttack: vi.fn() } };
});

const status = (over: Partial<AttackStatusT> = {}): AttackStatusT => ({ state: "idle", sent: 0, current: null, summary: null, error: null, ...over });
const summary = (over = {}) => ({ sent: 82, attacks: 51, attacks_stopped: 51, legit: 19, legit_passed: 19, uncounted: 12, unexpected: [], notes: [], ...over });

beforeEach(() => { vi.mocked(api.attackStatus).mockReset(); vi.mocked(api.startAttack).mockReset(); });

describe("AttackDemoBar", () => {
  it("offers the button and does nothing until it is pressed", async () => {
    vi.mocked(api.attackStatus).mockResolvedValue(status());
    render(<AttackDemoBar pollMs={5} />);
    expect(await screen.findByRole("button", { name: "Run test attack" })).toBeEnabled();
    expect(api.startAttack).not.toHaveBeenCalled();
    expect(screen.queryByText(/sent/)).not.toBeInTheDocument();
  });

  it("starts a run, shows the count and the current attack climbing, then the result", async () => {
    vi.mocked(api.attackStatus).mockResolvedValueOnce(status());
    vi.mocked(api.startAttack).mockResolvedValue(status({ state: "running" }));
    vi.mocked(api.attackStatus)
      .mockResolvedValueOnce(status({ state: "running", sent: 3, current: { owasp: "LLM01:2026", label: "prompt, base64", actual: "BLOCK" } }))
      .mockResolvedValueOnce(status({ state: "running", sent: 9, current: { owasp: "LLM04:2026", label: "malicious model file", actual: "BLOCK" } }))
      .mockResolvedValue(status({ state: "done", sent: 82, summary: summary() }));
    render(<AttackDemoBar pollMs={5} />);
    await userEvent.click(await screen.findByRole("button", { name: "Run test attack" }));
    expect(screen.getByRole("button", { name: "Attack running…" })).toBeDisabled();
    expect(await screen.findByText(/9 sent/)).toBeInTheDocument();
    expect(screen.getByText(/malicious model file/)).toBeInTheDocument();
    expect(await screen.findByText(/Finished: 51 of 51 attacks stopped, 19 of 19 normal requests passed/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run test attack" })).toBeEnabled();
  });

  it("does not claim success when something got through", async () => {
    vi.mocked(api.attackStatus).mockResolvedValue(status({ state: "done", summary: summary({ attacks_stopped: 50, unexpected: ["ask for the system prompt -> ALLOW"] }) }));
    render(<AttackDemoBar pollMs={5} />);
    expect(await screen.findByText(/50 of 51 attacks stopped/)).toBeInTheDocument();
    expect(screen.getByText(/Unexpected: ask for the system prompt -> ALLOW/)).toBeInTheDocument();
  });

  it("follows a run that is already going when the page opens, and when the press is refused as a second one", async () => {
    vi.mocked(api.attackStatus).mockResolvedValue(status({ state: "running", sent: 4 }));
    render(<AttackDemoBar pollMs={5} />);
    expect(await screen.findByText(/4 sent/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Attack running…" })).toBeDisabled();
  });

  it("follows the run when the gateway says one is already going", async () => {
    vi.mocked(api.attackStatus).mockResolvedValueOnce(status()).mockResolvedValue(status({ state: "running", sent: 7 }));
    vi.mocked(api.startAttack).mockRejectedValue(new ApiError(409, "an attack run is already going"));
    render(<AttackDemoBar pollMs={5} />);
    await userEvent.click(await screen.findByRole("button", { name: "Run test attack" }));
    expect(await screen.findByText(/7 sent/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("says what is missing when there is no demo harness, and does not offer the button", async () => {
    vi.mocked(api.attackStatus).mockResolvedValue(status({ state: "unavailable" }));
    render(<AttackDemoBar pollMs={5} />);
    expect(await screen.findByText(/Needs the demo harness/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run test attack" })).toBeDisabled();
  });

  it("shows a failed run and a failed start instead of staying silent", async () => {
    vi.mocked(api.attackStatus).mockResolvedValue(status({ state: "failed", error: "RuntimeError: boom" }));
    render(<AttackDemoBar pollMs={5} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The run stopped: RuntimeError: boom");
    vi.mocked(api.startAttack).mockRejectedValue(new ApiError(500, "gateway error"));
    await userEvent.click(screen.getByRole("button", { name: "Run test attack" }));
    await waitFor(() => expect(screen.getAllByRole("alert").some((a) => a.textContent === "gateway error")).toBe(true));
  });
});
