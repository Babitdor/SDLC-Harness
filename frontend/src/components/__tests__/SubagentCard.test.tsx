import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SubagentCard from "../SubagentCard";
import type { SubagentInfo } from "../../lib/types";

describe("SubagentCard", () => {
  it("should render the agent name", () => {
    const subagent: SubagentInfo = {
      name: "architecture",
      path: ["orchestrator", "architecture"],
      status: "completed",
      messages: [],
      toolCalls: [],
    };
    render(<SubagentCard subagent={subagent} />);
    expect(screen.getByText("Architecture")).toBeTruthy();
  });

  it("should show RUNNING status for started agents", () => {
    const subagent: SubagentInfo = {
      name: "ingestion",
      path: ["orchestrator", "ingestion"],
      status: "started",
      messages: [],
      toolCalls: [],
    };
    render(<SubagentCard subagent={subagent} />);
    expect(screen.getByText("RUNNING")).toBeTruthy();
  });

  it("should show COMPLETE status for completed agents", () => {
    const subagent: SubagentInfo = {
      name: "architecture",
      path: ["orchestrator", "architecture"],
      status: "completed",
      messages: [],
      toolCalls: [],
    };
    render(<SubagentCard subagent={subagent} />);
    expect(screen.getByText("COMPLETE")).toBeTruthy();
  });

  it("should show FAILED status for failed agents", () => {
    const subagent: SubagentInfo = {
      name: "architecture",
      path: ["orchestrator", "architecture"],
      status: "failed",
      messages: [],
      toolCalls: [],
    };
    render(<SubagentCard subagent={subagent} />);
    expect(screen.getByText("FAILED")).toBeTruthy();
  });

  it("should display the task description", () => {
    const subagent: SubagentInfo = {
      name: "architecture",
      path: ["orchestrator", "architecture"],
      status: "started",
      messages: [],
      toolCalls: [],
      task: "Generate BDD diagram",
    };
    const { container } = render(<SubagentCard subagent={subagent} />);
    expect(container.textContent).toContain("Generate BDD diagram");
  });

  it("should show elapsed time when startedAt is provided", () => {
    const subagent: SubagentInfo = {
      name: "architecture",
      path: ["orchestrator", "architecture"],
      status: "completed",
      messages: [],
      toolCalls: [],
      startedAt: Date.now() - 5000,
      completedAt: Date.now(),
    };
    render(<SubagentCard subagent={subagent} />);
    expect(screen.getByText(/[0-9]+S/)).toBeTruthy();
  });
});
