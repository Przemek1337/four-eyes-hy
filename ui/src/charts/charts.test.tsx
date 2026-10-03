import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BarList } from "./BarList";
import { LineChart } from "./LineChart";
import { StackedBars } from "./StackedBars";
import { niceMax } from "./scale";

const pts = [3, 5, 2, 0, 12, 7].map((v, i) => ({ t: 1_760_000_000 + i * 3600, v }));

describe("niceMax", () => {
  it("rounds an axis end up to a clean number and never below 1", () => {
    expect([0, 0.2, 1, 3, 7, 12, 48, 130, 4200].map(niceMax)).toEqual([1, 1, 1, 5, 10, 20, 50, 200, 5000]);
    expect(niceMax(Number.NaN)).toBe(1);
  });
});

describe("LineChart", () => {
  const chart = () => render(<LineChart title="Blocked per hour" seriesLabel="Blocked" points={pts} />);

  it("describes the series in words for screen readers and labels the latest value", () => {
    const { container } = chart();
    expect(screen.getByRole("img", { name: /Blocked: 29 in total, peak 12/ })).toBeInTheDocument();
    expect(container.querySelector(".end-label")).toHaveTextContent("7");
    expect(container.querySelectorAll(".grid").length).toBeGreaterThanOrEqual(2);
  });

  it("scales the axis to a clean maximum", () => {
    const { container } = chart();
    const ticks = [...container.querySelectorAll(".tick")].map((t) => t.textContent);
    expect(ticks).toContain("20"); // 12 rounds up to 20
    expect(ticks).toContain("0");
  });

  it("shows a tooltip on keyboard focus and moves with the arrow keys", async () => {
    chart();
    const plot = screen.getByRole("group", { name: /Blocked by time/ });
    act(() => plot.focus());
    expect(await screen.findByRole("status")).toHaveTextContent("7"); // latest point first
    await userEvent.keyboard("{ArrowLeft}");
    expect(screen.getByRole("status")).toHaveTextContent("12");
    await userEvent.keyboard("{Home}");
    expect(screen.getByRole("status")).toHaveTextContent("3");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("snaps the crosshair to the nearest point under the pointer", () => {
    chart();
    const plot = screen.getByRole("group", { name: /Blocked by time/ });
    fireEvent.pointerMove(plot, { clientX: 40 }); // far left of the plot
    expect(screen.getByRole("status")).toHaveTextContent("3");
    fireEvent.pointerLeave(plot);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("has a table view with the same numbers", async () => {
    chart();
    await userEvent.click(screen.getByRole("button", { name: "View as table" }));
    const rows = within(screen.getByRole("table")).getAllByRole("row");
    expect(rows).toHaveLength(pts.length + 1);
    expect(within(rows[5]).getByText("12")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "View as chart" }));
    expect(screen.getByRole("img")).toBeInTheDocument();
  });

  it("handles no data, one point and all zeros without breaking", () => {
    const { rerender } = render(<LineChart title="T" seriesLabel="Blocked" points={[]} />);
    expect(screen.getByText("No data in this window yet.")).toBeInTheDocument();
    rerender(<LineChart title="T" seriesLabel="Blocked" points={[{ t: 1, v: 4 }]} />);
    expect(screen.getByRole("img")).toBeInTheDocument();
    rerender(<LineChart title="T" seriesLabel="Blocked" points={pts.map((p) => ({ ...p, v: 0 }))} />);
    expect(screen.getByRole("img", { name: /0 in total/ })).toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain("NaN");
  });
});

describe("BarList", () => {
  const items = [
    { key: "a", label: "authz.tools", sub: "LLM03:2026", value: 22 },
    { key: "b", label: "sig.feed", sub: "LLM01:2026", value: 44 },
  ];
  it("ranks by value, leads with the biggest in the accent and shows the value at the tip", () => {
    const { container } = render(<BarList title="What stopped them" valueLabel="blocked" items={items} />);
    const rows = screen.getAllByRole("listitem");
    expect(rows[0]).toHaveTextContent("sig.feed");
    expect(rows[0]).toHaveTextContent("44");
    expect(container.querySelectorAll(".bl-track i.lead")).toHaveLength(1);
    expect(rows[0].querySelector(".lead")).not.toBeNull();
    expect((rows[1].querySelector("i") as HTMLElement).style.width).toBe("50%");
  });
  it("offers the same numbers as a table and an empty message", async () => {
    const { rerender } = render(<BarList title="What stopped them" valueLabel="blocked" items={items} />);
    await userEvent.click(screen.getByRole("button", { name: "View as table" }));
    expect(screen.getByRole("table")).toHaveTextContent("sig.feed (LLM01:2026)");
    rerender(<BarList title="What stopped them" valueLabel="blocked" items={[]} emptyText="Nothing yet." />);
    await userEvent.click(screen.getByRole("button", { name: "View as chart" }));
    expect(screen.getByText("Nothing yet.")).toBeInTheDocument();
  });
  it("renders hostile labels as text", () => {
    const { container } = render(<BarList title="t" valueLabel="x" items={[{ key: "h", label: "<img src=x onerror=alert(1)>", value: 1 }]} />);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
  });
});

describe("StackedBars", () => {
  const rows = [{ key: "p", label: "public", a: 320, b: 180 }, { key: "s", label: "bank_secret", a: 84, b: 0 }];
  it("always shows a legend, splits each bar with both parts and omits an empty part", () => {
    const { container } = render(<StackedBars title="Where data went" aLabel="Local model" bLabel="External model" rows={rows} />);
    expect(screen.getByRole("list", { name: "Legend" })).toHaveTextContent("Local model");
    expect(screen.getByRole("list", { name: "Legend" })).toHaveTextContent("External model");
    const [pub, secret] = container.querySelectorAll(".stack li");
    expect(pub.querySelectorAll(".st-bar i")).toHaveLength(2);
    expect(secret.querySelectorAll(".st-bar i")).toHaveLength(1); // no zero-width external sliver
    expect((pub.querySelector("i.a") as HTMLElement).style.width).toBe("64%");
  });
  it("lets the caller add a note per row and exposes a table", async () => {
    render(<StackedBars title="t" aLabel="Local" bLabel="External" rows={rows} note={(r) => (r.b === 0 ? <span>none external</span> : null)} />);
    expect(screen.getByText("none external")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "View as table" }));
    expect(screen.getByRole("table")).toHaveTextContent("bank_secret");
  });
});
