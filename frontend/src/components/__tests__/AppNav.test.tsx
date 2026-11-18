import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import AppNav from "../AppNav";

vi.mock("../ThemeToggle", () => ({ ThemeToggle: () => <span>theme</span> }));

function renderNav(overrides: Partial<Parameters<typeof AppNav>[0]> = {}) {
  const props = {
    tab: "threads" as const,
    onTabChange: vi.fn(),
    inspectorOpen: false,
    onToggleInspector: vi.fn(),
    health: { loading: false, connected: true, containerRunning: true },
    onToggleSidebar: vi.fn(),
    ...overrides,
  };
  render(<AppNav {...props} />);
  return props;
}

describe("AppNav", () => {
  it("renders every section tab and marks the active one", () => {
    renderNav({ tab: "mcp" });
    for (const label of ["THREADS", "AGENTS", "SKILLS", "MCP", "SETTINGS"]) {
      expect(screen.getByTitle(label)).toBeTruthy();
    }
    expect(screen.getByTitle("MCP").getAttribute("aria-current")).toBe("page");
  });

  it("switches section on tab click", () => {
    const props = renderNav();
    fireEvent.click(screen.getByTitle("AGENTS"));
    expect(props.onTabChange).toHaveBeenCalledWith("agents");
  });

  it("shows the gate state from health", () => {
    renderNav();
    expect(screen.getByText("GATE OPEN")).toBeTruthy();
  });
});
