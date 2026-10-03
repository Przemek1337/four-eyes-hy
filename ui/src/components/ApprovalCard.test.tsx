import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../api/client";
import { fx } from "../test/fixtures";
import { ApprovalCard } from "./ApprovalCard";

vi.mock("../api/client", () => ({ api: { decide: vi.fn() } }));

beforeEach(() => vi.mocked(api.decide).mockReset());

describe("ApprovalCard", () => {
  it("shows the real parameters, labels, rule, AI flag, the agent's reason and the bound hash", () => {
    render(<ApprovalCard approval={fx.approval()} />);
    expect(screen.getByRole("heading", { name: "Compliance needs to review this action" })).toBeInTheDocument();
    expect(screen.getByText("kyc-verify@external.example")).toBeInTheDocument();
    expect(screen.getByText("send_email")).toBeInTheDocument();
    expect(screen.getByText("flow.untrusted")).toBeInTheDocument();
    expect(screen.getByText("high_risk, untrusted, bank_secret")).toBeInTheDocument();
    expect(screen.getByText(/Inconsistent with the task \(0\.91\)/)).toBeInTheDocument();
    expect(screen.getByText("Agent’s reason")).toBeInTheDocument();
    expect(screen.getByText("“forward documents for verification”")).toBeInTheDocument();
    expect(screen.getByText("sha256 a1f3c9d2…7e8f")).toBeInTheDocument();
  });

  it("shows the two signature slots: the agent cannot sign, compliance is waiting", () => {
    render(<ApprovalCard approval={fx.approval()} />);
    expect(screen.getByText("Can’t approve its own action.")).toBeInTheDocument();
    expect(screen.getByText("Needs a second pair of eyes")).toBeInTheDocument();
  });

  it("makes Deny the primary button and Approve the secondary one", () => {
    render(<ApprovalCard approval={fx.approval()} />);
    expect(screen.getByRole("button", { name: "Deny" })).toHaveClass("primary");
    expect(screen.getByRole("button", { name: "Approve" })).not.toHaveClass("primary");
  });

  it("sends one decision even on a double click and then shows the outcome", async () => {
    let resolve!: (a: ReturnType<typeof fx.approval>) => void;
    vi.mocked(api.decide).mockReturnValue(new Promise((r) => { resolve = r; }));
    const onDecided = vi.fn();
    render(<ApprovalCard approval={fx.approval()} onDecided={onDecided} />);
    await userEvent.dblClick(screen.getByRole("button", { name: "Deny" }));
    expect(api.decide).toHaveBeenCalledTimes(1);
    expect(api.decide).toHaveBeenCalledWith("ap1", false);
    resolve(fx.approval({ status: "denied", decided_by: "compliance" }));
    expect(await screen.findByText("Denied by compliance")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Deny" })).not.toBeInTheDocument();
    expect(onDecided).toHaveBeenCalledTimes(1);
  });

  it("approves with the Approve button", async () => {
    vi.mocked(api.decide).mockResolvedValue(fx.approval({ status: "approved", decided_by: "compliance" }));
    render(<ApprovalCard approval={fx.approval()} />);
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(api.decide).toHaveBeenCalledWith("ap1", true);
    expect(await screen.findByText("Approved by compliance")).toBeInTheDocument();
  });

  it("shows the server error and allows another attempt", async () => {
    vi.mocked(api.decide).mockRejectedValueOnce(new Error("unknown approval")).mockResolvedValueOnce(fx.approval({ status: "denied", decided_by: "compliance" }));
    render(<ApprovalCard approval={fx.approval()} />);
    await userEvent.click(screen.getByRole("button", { name: "Deny" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("unknown approval");
    await userEvent.click(screen.getByRole("button", { name: "Deny" }));
    expect(await screen.findByText("Denied by compliance")).toBeInTheDocument();
  });

  it("renders parameters as text and tolerates a missing judge and agent reason", () => {
    const hostile = fx.approval({ args: { body: "<img src=x onerror=alert(1)>", nested: { a: 1 } }, judge: null, supplied_reason: null });
    const { container } = render(<ApprovalCard approval={hostile} />);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(screen.getByText('{"a":1}')).toBeInTheDocument();
    expect(screen.getByText("not run")).toBeInTheDocument();
    expect(screen.queryByText("Agent’s reason")).not.toBeInTheDocument();
  });

  it("does not offer buttons for an already decided approval", () => {
    render(<ApprovalCard approval={fx.approval({ status: "consumed", decided_by: "officer" })} />);
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.getByText("Used (approved by officer)")).toBeInTheDocument();
  });
});
