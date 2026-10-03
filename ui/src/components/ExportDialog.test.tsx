import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import userEvent from "@testing-library/user-event";
import { ExportDialog, OWASP_IDS } from "./ExportDialog";

const open = (onClose = () => {}) => render(<ExportDialog open onClose={onClose} />);

describe("ExportDialog", () => {
  it("renders nothing while closed", () => {
    render(<ExportDialog open={false} onClose={() => {}} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("starts with a JSONL export of everything and states that content is redacted", () => {
    open();
    expect(screen.getByRole("dialog", { name: "Export audit log" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download" })).toHaveAttribute("href", "/audit/export?format=jsonl");
    expect(screen.getByText("Export contains redacted content only")).toBeInTheDocument();
    expect(screen.getByText("GET /audit/export?format=jsonl")).toBeInTheDocument();
  });

  it("builds the URL from the chosen filters", async () => {
    open();
    await userEvent.click(screen.getByRole("button", { name: "CSV" }));
    await userEvent.selectOptions(screen.getByLabelText("Decision"), "BLOCK");
    await userEvent.selectOptions(screen.getByLabelText("OWASP category"), "LLM01:2026");
    await userEvent.type(screen.getByLabelText("Agent"), "kyc-agent");
    await userEvent.type(screen.getByLabelText("Session"), "sess_7f3a");
    await userEvent.type(screen.getByLabelText("Rule"), "authz.tools");
    expect(screen.getByRole("link", { name: "Download" })).toHaveAttribute(
      "href", "/audit/export?format=csv&decision=BLOCK&agent=kyc-agent&session=sess_7f3a&rule=authz.tools&owasp=LLM01%3A2026");
  });

  it("limits the time range with a preset or a custom range and ignores invalid input", async () => {
    open();
    await userEvent.selectOptions(screen.getByLabelText("Time range"), "hour");
    expect(screen.getByRole("link", { name: "Download" }).getAttribute("href")).toMatch(/from=20\d\d-/);
    await userEvent.selectOptions(screen.getByLabelText("Time range"), "custom");
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-10-03T14:00" } });
    expect(screen.getByRole("link", { name: "Download" }).getAttribute("href")).toMatch(/from=2026-10-0\d/);
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "" } });
    expect(screen.getByRole("link", { name: "Download" })).toHaveAttribute("href", "/audit/export?format=jsonl");
    await userEvent.selectOptions(screen.getByLabelText("Time range"), "all");
    expect(screen.queryByLabelText("From")).not.toBeInTheDocument();
  });

  it("exports only the chosen kinds of events and blocks an empty choice", async () => {
    open();
    await userEvent.click(screen.getByRole("checkbox", { name: "Budget and resource use" }));
    expect(screen.getByRole("link", { name: "Download" })).toHaveAttribute("href", "/audit/export?format=jsonl&events=decisions%2Cpolicy");
    await userEvent.click(screen.getByRole("checkbox", { name: "Decisions and threats" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "Policy changes and violations" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Pick at least one kind of event");
    expect(screen.queryByRole("link", { name: "Download" })).not.toBeInTheDocument();
    expect(screen.getByText("Download")).toHaveAttribute("aria-disabled", "true");
  });

  it("closes with Cancel, Escape, a click outside, and after Download", async () => {
    const onClose = vi.fn();
    const { unmount } = open(onClose);
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);
    fireEvent.mouseDown(document.querySelector(".modal-backdrop") as Element);
    expect(onClose).toHaveBeenCalledTimes(3);
    fireEvent.mouseDown(screen.getByRole("dialog")); // inside: stays open
    expect(onClose).toHaveBeenCalledTimes(3);
    unmount();
    const again = vi.fn();
    open(again);
    const link = screen.getByRole("link", { name: "Download" });
    link.addEventListener("click", (e) => e.preventDefault()); // jsdom cannot navigate to a download
    await userEvent.click(link);
    expect(again).toHaveBeenCalled();
  });

  it("keeps keyboard focus inside the dialog and returns it to the opener", async () => {
    const Host = () => {
      const [on, setOn] = useState(false);
      return <><button onClick={() => setOn(true)}>Export audit log</button><ExportDialog open={on} onClose={() => setOn(false)} /></>;
    };
    render(<Host />);
    const opener = screen.getByRole("button", { name: "Export audit log" });
    await userEvent.click(opener);
    expect(screen.getByRole("dialog")).toHaveFocus();
    await userEvent.tab({ shift: true }); // from the dialog itself backwards wraps to the last control
    expect(screen.getByRole("link", { name: "Download" })).toHaveFocus();
    await userEvent.tab(); // and forwards from the last wraps to the first
    expect(screen.getByLabelText("Time range")).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(opener).toHaveFocus();
  });

  it("offers all ten OWASP categories with the edition year", () => {
    expect(OWASP_IDS).toHaveLength(10);
    expect(OWASP_IDS[0]).toBe("LLM01:2026");
    expect(OWASP_IDS[9]).toBe("LLM10:2026");
  });
});
