import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Tabs, type TabDef } from "./Tabs";

const defs: TabDef<"a" | "b" | "c">[] = [{ id: "a", label: "Alpha" }, { id: "b", label: "Beta", attention: true }, { id: "c", label: "Gamma" }];

function Host() {
  const [v, setV] = useState<"a" | "b" | "c">("a");
  return <><Tabs tabs={defs} value={v} onChange={setV} label="Sections" /><p>current: {v}</p></>;
}

describe("Tabs", () => {
  it("renders a tablist with the selected tab marked and a dot on the one that needs attention", () => {
    render(<Host />);
    expect(screen.getByRole("tablist", { name: "Sections" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Alpha" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Beta needs attention" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Alpha" })).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("tab", { name: "Gamma" })).toHaveAttribute("tabindex", "-1");
  });

  it("selects on click", async () => {
    render(<Host />);
    await userEvent.click(screen.getByRole("tab", { name: "Gamma" }));
    expect(screen.getByText("current: c")).toBeInTheDocument();
  });

  it("moves with the arrow keys, wraps around and jumps with Home and End, keeping focus on the tab", async () => {
    render(<Host />);
    screen.getByRole("tab", { name: "Alpha" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByText("current: b")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Beta needs attention" })).toHaveFocus();
    await userEvent.keyboard("{End}");
    expect(screen.getByText("current: c")).toBeInTheDocument();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByText("current: a")).toBeInTheDocument(); // wrapped
    await userEvent.keyboard("{ArrowLeft}");
    expect(screen.getByText("current: c")).toBeInTheDocument();
    await userEvent.keyboard("{Home}");
    expect(screen.getByText("current: a")).toBeInTheDocument();
  });
});
