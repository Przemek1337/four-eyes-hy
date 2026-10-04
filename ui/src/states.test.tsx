import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "./api/client";
import App from "./App";
import { Async } from "./components/Async";
import { ConnectionBanner } from "./components/ConnectionBanner";
import { GatewayScreen } from "./components/GatewayScreen";
import { SessionList } from "./components/SessionList";
import { usePolling } from "./hooks/usePolling";
import { LiveProvider, OFFLINE_AFTER, useLive } from "./live";
import { fx } from "./test/fixtures";
import { SecurityView } from "./views/SecurityView";

class NoopEventSource { onopen = null; onerror = null; onmessage = null; close() {} }

beforeEach(() => vi.stubGlobal("EventSource", NoopEventSource));
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

const list = (data: string[]) => <ul>{data.map((x) => <li key={x}>{x}</li>)}</ul>;

describe("Async states", () => {
  it("holds the layout with a skeleton while loading, and says so to screen readers", () => {
    const { container } = render(<Async state={{ data: null, error: null, loading: true }}>{list}</Async>);
    const box = screen.getByRole("status");
    expect(box).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText("Loading…")).toHaveClass("sr-only");
    expect(container.querySelectorAll(".skeleton i")).toHaveLength(3);
  });

  it("offers Retry when it could not load, and only when it can retry", async () => {
    const refresh = vi.fn();
    const { rerender } = render(<Async state={{ data: null, error: "backend down", loading: false, refresh }}>{list}</Async>);
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load: backend down");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(refresh).toHaveBeenCalledTimes(1);
    rerender(<Async state={{ data: null, error: "backend down", loading: false }}>{list}</Async>);
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });

  it("keeps stale data visible and says when it is from, with a Retry", async () => {
    const refresh = vi.fn();
    const at = new Date("2026-10-03T14:17:02Z").getTime();
    render(<Async<string[]> state={{ data: ["a"], error: "timeout", loading: false, updatedAt: at, refresh }}>{list}</Async>);
    expect(screen.getByText("a")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/Showing the last data from \d\d:\d\d:\d\d; refresh failed: timeout/);
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(refresh).toHaveBeenCalled();
  });

  it("copes with stale data that has no timestamp, and with empty data", () => {
    const { rerender } = render(<Async<string[]> state={{ data: ["a"], error: "timeout", loading: false }}>{list}</Async>);
    expect(screen.getByRole("status")).toHaveTextContent("Showing the last data; refresh failed: timeout");
    rerender(<Async<string[]> state={{ data: [], error: null, loading: false }} isEmpty={(d) => d.length === 0} emptyText="No sessions yet.">{list}</Async>);
    expect(screen.getByText("No sessions yet.")).toBeInTheDocument();
  });
});

describe("polling and the connection", () => {
  function Probe({ fetcher, id = "p" }: { fetcher: () => Promise<string>; id?: string }) {
    const { data, updatedAt } = usePolling(fetcher, [], 1000);
    const { offline } = useLive();
    return <div><span>{id}:{data ?? "none"}</span><span>{id}-at:{updatedAt ? "set" : "unset"}</span><span>offline:{String(offline)}</span></div>;
  }

  it("records when data last loaded", async () => {
    render(<LiveProvider><Probe fetcher={() => Promise.resolve("v")} /></LiveProvider>);
    await waitFor(() => expect(screen.getByText("p-at:set")).toBeInTheDocument());
  });

  it("counts the gateway as not responding after several failed polls in a row, and recovers on the first success", async () => {
    let fail = true;
    const fetcher = () => (fail ? Promise.reject(new Error("down")) : Promise.resolve("v"));
    const probes = Array.from({ length: OFFLINE_AFTER }, (_, i) => <Probe key={i} id={`p${i}`} fetcher={fetcher} />);
    render(<LiveProvider>{probes}</LiveProvider>);
    await waitFor(() => expect(screen.getAllByText("offline:true").length).toBeGreaterThan(0));
    fail = false; // the next scheduled poll succeeds
    await waitFor(() => expect(screen.getAllByText("offline:false").length).toBeGreaterThan(0), { timeout: 2500 });
  });

  it("stays online when only some of the polls fail", async () => {
    render(<LiveProvider>
      <Probe id="ok" fetcher={() => Promise.resolve("v")} />
      <Probe id="bad" fetcher={() => Promise.reject(new Error("500"))} />
    </LiveProvider>);
    await waitFor(() => expect(screen.getByText("ok:v")).toBeInTheDocument());
    expect(screen.getAllByText("offline:false").length).toBe(2);
  });
});

describe("ConnectionBanner", () => {
  function Failing() {
    usePolling(() => Promise.reject(new Error("down")), []);
    usePolling(() => Promise.reject(new Error("down")), []);
    usePolling(() => Promise.reject(new Error("down")), []);
    return null;
  }

  it("says nothing while the gateway answers", () => {
    render(<LiveProvider><ConnectionBanner /></LiveProvider>);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("once data has loaded, explains that panels show old data, and Retry now polls again", async () => {
    let up = true;
    const fetchSpy = vi.fn(() => (up ? Promise.resolve("v") : Promise.reject(new Error("down"))));
    vi.stubGlobal("fetch", fetchSpy);
    function Probe() {
      const { refreshNow } = useLive();
      usePolling(() => fetch("/x").then((r) => String(r)), []);
      usePolling(() => fetch("/y").then((r) => String(r)), []);
      usePolling(() => fetch("/z").then((r) => String(r)), []);
      return <button onClick={refreshNow}>poke</button>;
    }
    render(<LiveProvider><ConnectionBanner /><GatewayScreen /><Probe /></LiveProvider>);
    await waitFor(() => expect(screen.queryByText("Connecting to the gateway…")).not.toBeInTheDocument());
    up = false;
    await userEvent.click(screen.getByRole("button", { name: "poke" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The gateway is not responding");
    expect(alert).toHaveTextContent("last data they loaded");
    const before = fetchSpy.mock.calls.length;
    await userEvent.click(screen.getByRole("button", { name: "Retry now" }));
    await waitFor(() => expect(fetchSpy.mock.calls.length).toBeGreaterThan(before));
  });
});

describe("GatewayScreen", () => {
  function Failing() {
    usePolling(() => Promise.reject(new Error("down")), []);
    usePolling(() => Promise.reject(new Error("down")), []);
    usePolling(() => Promise.reject(new Error("down")), []);
    return null;
  }

  it("says it is connecting while nothing has answered yet, with the four eyes", () => {
    const { container } = render(<LiveProvider><GatewayScreen /></LiveProvider>);
    expect(screen.getByText("Connecting to the gateway…")).toBeInTheDocument();
    expect(container.querySelectorAll(".gw-eyes i")).toHaveLength(4);
    expect(container.querySelector(".gw-eyes")).toHaveAttribute("aria-hidden", "true");
  });

  it("says the gateway is not responding, how to start it, and Retry now polls again", async () => {
    const fetchSpy = vi.fn(() => Promise.reject(new Error("down")));
    vi.stubGlobal("fetch", fetchSpy);
    function Probes() {
      usePolling(() => fetch("/a").then((r) => r.text()), []);
      usePolling(() => fetch("/b").then((r) => r.text()), []);
      usePolling(() => fetch("/c").then((r) => r.text()), []);
      return null;
    }
    render(<LiveProvider><GatewayScreen /><Probes /></LiveProvider>);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The gateway is not responding.");
    expect(alert).toHaveTextContent("make run");
    const before = fetchSpy.mock.calls.length;
    await userEvent.click(screen.getByRole("button", { name: "Retry now" }));
    await waitFor(() => expect(fetchSpy.mock.calls.length).toBeGreaterThan(before));
  });

  it("goes away on the first answer, and does not come back when the gateway drops later", async () => {
    let up = false;
    function Probes() {
      const { refreshNow } = useLive();
      for (const id of ["a", "b", "c"]) usePolling(() => (up ? Promise.resolve(id) : Promise.reject(new Error("down"))), []);
      return <button onClick={refreshNow}>poke</button>;
    }
    render(<LiveProvider><GatewayScreen /><ConnectionBanner /><Probes /></LiveProvider>);
    expect(await screen.findByText("The gateway is not responding.")).toBeInTheDocument();
    up = true;
    await userEvent.click(screen.getByRole("button", { name: "poke" }));
    await waitFor(() => expect(screen.queryByText("The gateway is not responding.")).not.toBeInTheDocument());
    up = false;
    await userEvent.click(screen.getByRole("button", { name: "poke" }));
    expect(await screen.findByText(/last data they loaded/)).toBeInTheDocument();   // the banner, not the full screen
    expect(screen.queryByText(/make run/)).not.toBeInTheDocument();
  });
});

describe("the sidebar and the app", () => {
  it("shows checking while nothing is known, then offline with a banner when every poll fails", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new Error("down")));
    render(<App />);
    expect(document.querySelector(".side-foot")).toHaveTextContent("Checking every 5 s");
    expect(document.querySelector(".side-foot .ring")).not.toBeNull();
    await userEvent.click(screen.getByRole("tab", { name: "Management" })); // many panels poll at once
    expect(await screen.findByText("The gateway is not responding.")).toBeInTheDocument();
    expect(document.querySelector(".side-foot")).toHaveTextContent("Offline");
    expect(document.querySelector(".side-foot .off")).not.toBeNull();
  });

  it("shows live once the event stream opens", async () => {
    const streams: { onopen: (() => void) | null }[] = [];
    class Stream { onopen: (() => void) | null = null; onerror = null; onmessage = null; constructor() { streams.push(this); } close() {} }
    vi.stubGlobal("EventSource", Stream);
    vi.stubGlobal("fetch", () => new Promise(() => {}));
    await act(async () => { render(<App />); });
    expect(document.querySelector(".side-foot")).toHaveTextContent("Checking every 5 s");
    await act(async () => { streams[0].onopen?.(); });
    expect(document.querySelector(".side-foot")).toHaveTextContent("Live");
    expect(document.querySelector(".side-foot .live")).not.toBeNull();
  });

  it("sends someone with no sessions to the Playground", async () => {
    vi.stubGlobal("fetch", (url: string) => Promise.resolve(new Response(JSON.stringify(String(url).startsWith("/admin/sessions") ? { sessions: [] } : { approvals: [] }), { status: 200 })));
    render(<App />);
    expect(await screen.findByText("No sessions yet")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open Playground" }));
    expect(screen.getByRole("tab", { name: "Playground" })).toHaveAttribute("aria-selected", "true");
  });
});

describe("empty sessions list", () => {
  const noop = () => {};
  it("tells a new user what to do, with a way to Chat when there is one", async () => {
    const onOpenPlayground = vi.fn();
    const { rerender } = render(<SessionList rows={[]} onSelect={noop} filters={{}} onFilters={noop} onOpenPlayground={onOpenPlayground} />);
    expect(screen.getByText("No sessions yet")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open Playground" }));
    expect(onOpenPlayground).toHaveBeenCalled();
    rerender(<SessionList rows={[]} onSelect={noop} filters={{}} onFilters={noop} />);
    expect(screen.queryByRole("button", { name: "Open Playground" })).not.toBeInTheDocument();
  });

  it("explains an empty result of filters and clears them", async () => {
    const onFilters = vi.fn();
    render(<SessionList rows={[]} onSelect={noop} filters={{ decision: "BLOCK", agent: "x" }} onFilters={onFilters} />);
    expect(screen.getByText("No sessions match these filters")).toBeInTheDocument();
    expect(screen.queryByText("No sessions yet")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(onFilters).toHaveBeenCalledWith({});
  });
});

vi.mock("./api/client", async (orig) => {
  const real = await orig<typeof import("./api/client")>();
  return { ...real, api: { ...real.api, sessions: vi.fn(), approvals: vi.fn(), session: vi.fn() } };
});

describe("Security view errors", () => {
  it("offers Retry when the sessions cannot be loaded and recovers", async () => {
    vi.mocked(api.approvals).mockResolvedValue({ approvals: [] });
    vi.mocked(api.sessions).mockRejectedValueOnce(new Error("backend down")).mockResolvedValue({ sessions: [fx.session()] });
    render(<LiveProvider><SecurityView /></LiveProvider>);
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load sessions: backend down");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("button", { name: "a41f" })).toBeInTheDocument();
  });
});
