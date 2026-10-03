import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../api/client";
import { fx } from "../test/fixtures";
import { SecurityView } from "./SecurityView";

vi.mock("../api/client", () => ({
  api: { sessions: vi.fn(), approvals: vi.fn(), session: vi.fn(), decide: vi.fn() },
  exportUrl: vi.fn(() => "/audit/export?format=jsonl"),
}));

const second = fx.session({ session_id: "b2", status: "clean", labels: [], data_class: "public", blocked_count: 0, pending_approvals: 1 });

beforeEach(() => {
  vi.mocked(api.sessions).mockResolvedValue({ sessions: [fx.session(), second] });
  vi.mocked(api.approvals).mockResolvedValue({ approvals: [fx.approval({ session_id: "b2" })] });
  vi.mocked(api.session).mockImplementation(async (id: string) => ({
    session: { ...fx.session({ session_id: id }), scope: {}, task: null }, events: [], approvals: [],
  }));
});

describe("SecurityView", () => {
  it("opens on the list with the approval queue first", async () => {
    render(<SecurityView />);
    expect(await screen.findByRole("button", { name: "a41f" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Security" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Pending approvals (1)" })).toBeInTheDocument();
  });

  it("opens the session behind a pending approval and goes back", async () => {
    render(<SecurityView />);
    await userEvent.click(await screen.findByRole("button", { name: "Review" }));
    expect(await screen.findByRole("region", { name: "Session detail" })).toHaveTextContent("b2");
    await userEvent.click(screen.getByRole("button", { name: "← Sessions" }));
    expect(await screen.findByRole("button", { name: "a41f" })).toBeInTheDocument();
  });

  it("opens a session from the table", async () => {
    render(<SecurityView />);
    await userEvent.click(await screen.findByRole("button", { name: "a41f" }));
    expect(await screen.findByRole("region", { name: "Session detail" })).toHaveTextContent("a41f");
  });

  it("explains a failed load instead of crashing", async () => {
    vi.mocked(api.sessions).mockRejectedValue(new Error("backend down"));
    render(<SecurityView />);
    expect(await screen.findByRole("alert")).toHaveTextContent("backend down");
  });
});
