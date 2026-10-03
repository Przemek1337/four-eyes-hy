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
});
