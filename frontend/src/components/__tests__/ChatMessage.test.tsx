import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ChatMessage from "../ChatMessage";
import type { ChatMessage as ChatMessageType } from "../../lib/types";

describe("ChatMessage", () => {
  it("should render user messages right-aligned with YOU label", () => {
    const msg: ChatMessageType = {
      id: "m1",
      role: "user",
      content: "Hello world",
      timestamp: 1000,
    };
    render(<ChatMessage message={msg} />);
    expect(screen.getByText("YOU")).toBeTruthy();
    expect(screen.getByText("Hello world")).toBeTruthy();
  });

  it("should render assistant messages with ORCHESTRATOR label", () => {
    const msg: ChatMessageType = {
      id: "m2",
      role: "assistant",
      content: "I can help with that",
      timestamp: 1000,
    };
    render(<ChatMessage message={msg} />);
    expect(screen.getByText("ORCHESTRATOR")).toBeTruthy();
    expect(screen.getByText("I can help with that")).toBeTruthy();
  });

  it("should render agent-specific assistant messages with agent name", () => {
    const msg: ChatMessageType = {
      id: "m3",
      role: "assistant",
      content: "Generating ADR",
      timestamp: 1000,
      agentName: "architecture",
    };
    render(<ChatMessage message={msg} />);
    expect(screen.getByText("ARCHITECTURE")).toBeTruthy();
  });

  it("should render system notes with NOTE label", () => {
    const msg: ChatMessageType = {
      id: "m4",
      role: "system",
      content: "System initialized",
      timestamp: 1000,
    };
    render(<ChatMessage message={msg} />);
    expect(screen.getByText("— NOTE —")).toBeTruthy();
    expect(screen.getByText("System initialized")).toBeTruthy();
  });

  it("should render trace URL for system messages", () => {
    const msg: ChatMessageType = {
      id: "m5",
      role: "system",
      content: "Done",
      timestamp: 1000,
      traceUrl: "https://smith.langchain.com/traces/abc",
    };
    render(<ChatMessage message={msg} />);
    expect(screen.getByText("TRACE ↗")).toBeTruthy();
  });

  it("should render user attachments", () => {
    const msg: ChatMessageType = {
      id: "m6",
      role: "user",
      content: "See attached",
      timestamp: 1000,
      attachments: [{ name: "report.pdf", path: "/workspace/report.pdf" }],
    };
    render(<ChatMessage message={msg} />);
    expect(screen.getByText("report.pdf")).toBeTruthy();
  });

  it("should show empty message placeholder for user messages without content", () => {
    const msg: ChatMessageType = {
      id: "m7",
      role: "user",
      content: "",
      timestamp: 1000,
    };
    render(<ChatMessage message={msg} />);
    expect(screen.getByText("(empty message)")).toBeTruthy();
  });

  it("should render subagent cards when subagents are provided", () => {
    const msg: ChatMessageType = {
      id: "m8",
      role: "assistant",
      content: "Working...",
      timestamp: 1000,
    };
    const subagents = [
      {
        name: "architecture",
        path: ["orchestrator", "architecture"],
        status: "completed" as const,
        messages: [],
        toolCalls: [],
      },
    ];
    render(<ChatMessage message={msg} subagents={subagents} />);
    expect(screen.getByText("Architecture")).toBeTruthy();
  });

  it("shows a plain-English activity label by default, raw tool name behind the toggle", async () => {
    const msg: ChatMessageType = {
      id: "m9",
      role: "assistant",
      content: "",
      timestamp: 1000,
      toolCalls: [
        {
          toolId: "t1",
          toolName: "write_file",
          toolArgs: '{"file_path": "/test.md"}',
        },
      ],
    };
    const { container } = render(<ChatMessage message={msg} />);
    // Default (non-technical) view: plain English, no raw tool name.
    expect(container.textContent).toContain("Writing documents…");
    expect(container.textContent).not.toContain("WRITE FILE");
    // Opting into technical details reveals the raw ToolCallBlock.
    fireEvent.click(screen.getByText("Show technical details →"));
    expect(container.textContent).toContain("WRITE FILE");
  });

  it("describes a task delegation in plain English by default", () => {
    const msg: ChatMessageType = {
      id: "m10",
      role: "assistant",
      content: "",
      timestamp: 1000,
      toolCalls: [
        {
          toolId: "t1",
          toolName: "task",
          toolArgs: '{"subagent_type": "architecture"}',
        },
      ],
    };
    const { container } = render(<ChatMessage message={msg} />);
    // With no subagent feed present, the delegation still surfaces — as a
    // plain-English step, not the raw "DELEGATE → ARCHITECTURE" tool label.
    expect(container.textContent).toContain("Delegating to Architecture…");
    expect(container.textContent).not.toContain("DELEGATE");
  });

  it("shows a collapsible THINKING PROCESS section when message has reasoning", () => {
    const msg: ChatMessageType = {
      id: "m11",
      role: "assistant",
      content: "Final answer",
      timestamp: 1000,
      reasoning: "Step-by-step reasoning trace...",
    };
    render(<ChatMessage message={msg} />);

    // Should show the THINKING PROCESS button collapsed by default
    expect(screen.getByText("THINKING PROCESS")).toBeTruthy();
    expect(screen.getByText("EXPAND")).toBeTruthy();

    // Reasoning content should not be visible initially
    expect(screen.queryByText("Step-by-step reasoning trace...")).toBeNull();

    // Click to expand
    fireEvent.click(screen.getByText("THINKING PROCESS"));

    // Reasoning content should now be visible
    expect(screen.getByText("Step-by-step reasoning trace...")).toBeTruthy();
    expect(screen.getByText("COLLAPSE")).toBeTruthy();

    // Click to collapse
    fireEvent.click(screen.getByText("COLLAPSE"));

    // Reasoning content should be hidden again
    expect(screen.queryByText("Step-by-step reasoning trace...")).toBeNull();
  });

  it("does not show THINKING PROCESS section when message has no reasoning", () => {
    const msg: ChatMessageType = {
      id: "m12",
      role: "assistant",
      content: "No reasoning here",
      timestamp: 1000,
    };
    render(<ChatMessage message={msg} />);
    expect(screen.queryByText("THINKING PROCESS")).toBeNull();
  });
});
