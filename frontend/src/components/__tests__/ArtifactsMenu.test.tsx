import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ArtifactsMenu from "../ArtifactsMenu";

const ARTIFACTS = [
  { name: "requirements/USER_STORIES.md", phase: "requirements" as const, status: "ready" as const, agent: "requirements" },
  { name: "design/openapi.yaml", phase: "design" as const, status: "pending" as const, agent: "api" },
];

function renderMenu(overrides: Partial<Parameters<typeof ArtifactsMenu>[0]> = {}) {
  const props = {
    artifacts: ARTIFACTS,
    selectedArtifact: null,
    onSelectArtifact: vi.fn(),
    inspectorOpen: false,
    onToggleInspector: vi.fn(),
    ...overrides,
  };
  render(<ArtifactsMenu {...props} />);
  return props;
}

describe("ArtifactsMenu", () => {
  it("shows the ready count on the closed button", () => {
    renderMenu();
    expect(screen.getByTitle("Artifacts")).toBeTruthy();
    expect(screen.getByText("01")).toBeTruthy();
  });

  it("opens with ready/pending entries listed by basename", () => {
    renderMenu();
    fireEvent.click(screen.getByTitle("Artifacts"));

    expect(screen.getByText("SPECIFICATIONS")).toBeTruthy();
    expect(screen.getByText("USER_STORIES.md")).toBeTruthy();
    expect(screen.getByText("openapi.yaml")).toBeTruthy();
    expect(screen.getByText("1/2")).toBeTruthy();
  });

  it("selects a ready artifact and closes the menu", () => {
    const props = renderMenu();
    fireEvent.click(screen.getByTitle("Artifacts"));
    fireEvent.click(screen.getByText("USER_STORIES.md"));

    expect(props.onSelectArtifact).toHaveBeenCalledWith("requirements/USER_STORIES.md");
    expect(screen.queryByText("SPECIFICATIONS")).toBeNull();
  });

  it("keeps pending artifacts listed but inert", () => {
    const props = renderMenu();
    fireEvent.click(screen.getByTitle("Artifacts"));

    const pendingRow = screen.getByText("openapi.yaml").closest("button");
    expect(pendingRow?.disabled).toBe(true);
    fireEvent.click(screen.getByText("openapi.yaml"));
    expect(props.onSelectArtifact).not.toHaveBeenCalled();
  });

  it("says so when no artifacts exist yet", () => {
    renderMenu({ artifacts: [] });
    fireEvent.click(screen.getByTitle("Artifacts"));
    expect(screen.getByText(/No artifacts yet/)).toBeTruthy();
  });

  it("routes the inspector action and flips its label", () => {
    const props = renderMenu();
    fireEvent.click(screen.getByTitle("Artifacts"));
    fireEvent.click(screen.getByText("OPEN INSPECTOR →"));
    expect(props.onToggleInspector).toHaveBeenCalled();

    renderMenu({ inspectorOpen: true });
    fireEvent.click(screen.getAllByTitle("Artifacts")[1]);
    expect(screen.getByText("CLOSE INSPECTOR")).toBeTruthy();
  });
});
