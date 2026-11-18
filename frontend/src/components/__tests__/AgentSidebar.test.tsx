import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import AgentSidebar from "../AgentSidebar";

describe("AgentSidebar", () => {
  const defaultProps = {
    projectId: "default",
    onProjectIdChange: vi.fn(),
    onCreateProject: vi.fn(),
    artifacts: [],
    onRefreshArtifacts: vi.fn(),
    onArtifactClick: vi.fn(),
    selectedArtifact: null,
    tracing: null,
    open: true,
    onClose: vi.fn(),
    onAgentClick: vi.fn(),
  };

  it("should render the SDLC Harness title", () => {
    render(<AgentSidebar {...defaultProps} />);
    expect(screen.getByText("SDLC Harness")).toBeTruthy();
  });

  it("should render project ID input", () => {
    render(<AgentSidebar {...defaultProps} />);
    const input = document.querySelector('input[type="text"]');
    expect(input).toBeTruthy();
  });

  it("should render the agent pipeline section", () => {
    render(<AgentSidebar {...defaultProps} />);
    expect(screen.getByText("Agent Pipeline")).toBeTruthy();
  });

  it("should render the artifacts section", () => {
    render(<AgentSidebar {...defaultProps} />);
    expect(screen.getByText("Artifacts")).toBeTruthy();
  });

  it("should show no artifacts message when list is empty", () => {
    const { container } = render(<AgentSidebar {...defaultProps} />);
    expect(container.textContent).toContain("No artifacts yet");
  });

  it("should render artifact items when provided", () => {
    const artifacts = [
      { name: "requirements/REQUIREMENTS.md", phase: "requirements" as const, status: "ready" as const, agent: "ingestion" },
      { name: "diagrams/class.mmd", phase: "diagrams" as const, status: "pending" as const, agent: "diagram" },
    ];
    const { container } = render(<AgentSidebar {...defaultProps} artifacts={artifacts} />);
    expect(container.textContent).toContain("REQUIREMENTS.md");
    expect(container.textContent).toContain("class.mmd");
  });

  it("should show LangSmith tracing info when provided", () => {
    const tracing = { enabled: true, project: "sdlc-harness", endpoint: "https://api.smith.langchain.com", status: "connected", api_key_set: true };
    const { container } = render(<AgentSidebar {...defaultProps} tracing={tracing} />);
    expect(container.textContent).toContain("LangSmith");
    expect(container.textContent).toContain("sdlc-harness");
  });

  it("should be hidden when open is false", () => {
    const { container } = render(<AgentSidebar {...defaultProps} open={false} />);
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("-translate-x-full");
  });
});