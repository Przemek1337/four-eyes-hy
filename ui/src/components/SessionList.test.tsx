import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fx } from "../test/fixtures";
import { ApprovalQueue } from "./ApprovalQueue";
import { SessionList } from "./SessionList";

const clean = fx.session({ session_id: "b2", status: "clean", labels: [], data_class: "public", blocked_count: 0, pending_approvals: 0, last_decision: "ALLOW", client: null });

describe("SessionList", () => {
  it("lists sessions with agent, client, status and last decision", () => {
    render(<SessionList rows={[fx.session(), clean]} onSelect={() => {}} filters={{}} onFilters={() => {}} />);
    const row = screen.getByRole("button", { name: "a41f" }).closest(".srow") as HTMLElement;
    expect(row).toHaveTextContent("kyc-agent");
    expect(row).toHaveTextContent("Nowak Logistics");
    expect(row).toHaveTextContent("High risk");
    expect(row).toHaveTextContent("APPROVAL");
    const plain = screen.getByRole("button", { name: "b2" }).closest(".srow") as HTMLElement;
    expect(plain).toHaveTextContent("Clean");
    expect(plain).toHaveTextContent("–"); // no client
  });

  it("opens a session from the id or from anywhere in the row", async () => {
    const onSelect = vi.fn();
    render(<SessionList rows={[fx.session(), clean]} onSelect={onSelect} filters={{}} onFilters={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "b2" }));
    expect(onSelect).toHaveBeenCalledWith("b2");
    await userEvent.click(screen.getByText("Nowak Logistics"));
    expect(onSelect).toHaveBeenLastCalledWith("a41f");
  });

  it("reports quick filters and field filters", async () => {
    const onFilters = vi.fn();
    render(<SessionList rows={[fx.session()]} onSelect={() => {}} filters={{}} onFilters={onFilters} />);
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: "Blocked" }));
    expect(onFilters).toHaveBeenCalledWith({ decision: "BLOCK" });
    await userEvent.click(screen.getByRole("button", { name: "Needs approval" }));
    expect(onFilters).toHaveBeenLastCalledWith({ decision: "APPROVAL" });
    await userEvent.selectOptions(screen.getByLabelText("Data class"), "public");
    expect(onFilters).toHaveBeenLastCalledWith({ data_class: "public" });
    await userEvent.type(screen.getByLabelText("Agent"), "k");
    expect(onFilters).toHaveBeenLastCalledWith({ agent: "k" });
  });

  it("marks the active quick filter and shows an empty state", () => {
    render(<SessionList rows={[]} onSelect={() => {}} filters={{ decision: "BLOCK" }} onFilters={() => {}} />);
    expect(screen.getByRole("button", { name: "Blocked" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("No sessions match.")).toBeInTheDocument();
  });
});

describe("ApprovalQueue", () => {
  it("names what waits and opens the owning session", async () => {
    const onOpen = vi.fn();
    render(<ApprovalQueue approvals={[fx.approval()]} onOpen={onOpen} />);
    const bar = screen.getByRole("region", { name: "Pending approvals (1)" });
    expect(bar).toHaveTextContent("1 action waiting for compliance");
    expect(bar).toHaveTextContent("send_email to kyc-verify@external.example");
    await userEvent.click(screen.getByRole("button", { name: "Review" }));
    expect(onOpen).toHaveBeenCalledWith("a41f");
  });
  it("counts several waiting actions", () => {
    render(<ApprovalQueue approvals={[fx.approval(), fx.approval({ id: "ap2", session_id: "b2" })]} onOpen={() => {}} />);
    expect(screen.getByRole("region", { name: "Pending approvals (2)" })).toHaveTextContent("2 actions waiting for compliance");
  });
  it("says so when nothing waits", () => {
    render(<ApprovalQueue approvals={[]} onOpen={() => {}} />);
    expect(screen.getByText("No approvals waiting.")).toBeInTheDocument();
  });
});
