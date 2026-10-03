import { act, render, screen, waitFor } from "@testing-library/react";
import { LiveProvider, useLive } from "../live";
import { useEventStream } from "./useEventStream";
import { usePolling } from "./usePolling";

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((m: { data: string }) => void) | null = null;
  closed = false;
  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }
  close() {
    this.closed = true;
  }
}

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function Probe({ fetcher }: { fetcher: () => Promise<string> }) {
  const { data, error, loading } = usePolling(fetcher, [], 1000);
  const { connected } = useLive();
  return (
    <div>
      <span>data:{data ?? "none"}</span>
      <span>error:{error ?? "none"}</span>
      <span>loading:{String(loading)}</span>
      <span>connected:{String(connected)}</span>
    </div>
  );
}

describe("usePolling", () => {
  it("loads, then keeps the last data when a refresh fails", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetcher = vi.fn().mockResolvedValueOnce("first").mockRejectedValue(new Error("backend down"));
    render(<Probe fetcher={fetcher} />);
    await waitFor(() => expect(screen.getByText("data:first")).toBeInTheDocument());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1100);
    });
    expect(screen.getByText("data:first")).toBeInTheDocument();
    expect(screen.getByText("error:backend down")).toBeInTheDocument();
    expect(screen.getByText("loading:false")).toBeInTheDocument();
  });

  it("reports an error without data when the first load fails", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("nope"));
    render(<Probe fetcher={fetcher} />);
    await waitFor(() => expect(screen.getByText("error:nope")).toBeInTheDocument());
    expect(screen.getByText("data:none")).toBeInTheDocument();
  });
});

describe("live provider", () => {
  it("opens one event stream, tracks connection state and refetches on events", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const fetcher = vi.fn().mockResolvedValue("v");
    render(
      <LiveProvider>
        <Probe fetcher={fetcher} />
      </LiveProvider>,
    );
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    const es = FakeEventSource.instances[0];
    expect(es.url).toBe("/admin/stream");
    expect(screen.getByText("connected:false")).toBeInTheDocument();
    act(() => es.onopen?.());
    expect(screen.getByText("connected:true")).toBeInTheDocument();

    act(() => es.onmessage?.({ data: JSON.stringify({ event: "decision" }) }));
    act(() => es.onmessage?.({ data: "not json" })); // ignored, never throws
    await act(async () => {
      await vi.advanceTimersByTimeAsync(400);
    });
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2)); // one debounced refresh for the burst

    act(() => es.onerror?.());
    expect(screen.getByText("connected:false")).toBeInTheDocument();
  });

  it("closes the stream on unmount and tolerates browsers without EventSource", () => {
    const { unmount } = render(<LiveProvider><span>x</span></LiveProvider>);
    unmount();
    expect(FakeEventSource.instances[0].closed).toBe(true);
    vi.stubGlobal("EventSource", undefined);
    function Bare() {
      return <span>{String(useEventStream("/x", () => undefined))}</span>;
    }
    render(<Bare />);
    expect(screen.getByText("false")).toBeInTheDocument();
  });
});
