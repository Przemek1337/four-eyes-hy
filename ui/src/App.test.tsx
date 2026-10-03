import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

class NoopEventSource {
  onopen = null;
  onerror = null;
  onmessage = null;
  close() {}
}

beforeEach(() => {
  vi.stubGlobal("EventSource", NoopEventSource);
  vi.stubGlobal("fetch", () => new Promise(() => {})); // views start loading; never answer, so no late state updates
});
afterEach(() => vi.unstubAllGlobals());

describe("App shell", () => {
  it("shows the three views as sidebar tabs and starts on Security", () => {
    render(<App />);
    expect(screen.getByRole("tab", { name: "Security" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Management" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tab", { name: "Chat" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Security view" })).toBeInTheDocument();
  });

  it("switches views", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("tab", { name: "Management" }));
    expect(screen.getByRole("region", { name: "Management view" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Chat" }));
    expect(screen.getByRole("region", { name: "Chat view" })).toBeInTheDocument();
  });

  it("names the product for assistive technology", () => {
    render(<App />);
    expect(screen.getByRole("img", { name: "FourEyes" })).toBeInTheDocument();
  });

  it("tells the user when the live stream is not connected", () => {
    render(<App />);
    expect(screen.getByRole("status")).toHaveTextContent("Checking every 5 s");
  });

  it("opens the session of a chat document in the Security view", async () => {
    const json = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
    const session = { session_id: "doc-7", agent: "kyc-agent", client: null, started: 1, steps: 0, labels: [], data_class: "public",
      status: "clean", last_decision: null, blocked_count: 0, pending_approvals: 0 };
    vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
      const u = String(url);
      if (u === "/admin/chat" && init?.method === "POST") {
        return json({ session_id: "doc-7", decision: "ALLOW", rule: null, layer: null, code: null, owasp: [], data_class: "public", route: null,
          latency_ms: null, injection_score: null, reply: null, approval_id: null, message: "done",
          steps: [{ n: 1, tool: "read_document", args: {}, outcome: "ALLOW", code: null, approval_id: null }] });
      }
      if (u.startsWith("/admin/sessions/doc-7")) return json({ session: { ...session, scope: {}, task: null }, events: [], approvals: [] });
      if (u.startsWith("/admin/sessions")) return json({ sessions: [] });
      return json({ approvals: [] });
    });
    render(<App />);
    await userEvent.click(screen.getByRole("tab", { name: "Chat" }));
    await userEvent.click(screen.getByRole("button", { name: "Add an attachment" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Clean client document" }));
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    await userEvent.click(await screen.findByRole("button", { name: "Open this session in Security" }));
    expect(screen.getByRole("tab", { name: "Security" })).toHaveAttribute("aria-selected", "true");
    const detail = await screen.findByRole("region", { name: "Session detail" });
    expect(detail).toHaveTextContent("doc-7");
    expect(screen.getByRole("button", { name: "← Sessions" })).toBeInTheDocument();
  });
});
