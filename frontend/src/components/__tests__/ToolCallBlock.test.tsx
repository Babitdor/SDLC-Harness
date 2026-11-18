import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import ToolCallBlock from "../ToolCallBlock";

describe("ToolCallBlock", () => {
  it("should render the tool name in uppercase", () => {
    render(<ToolCallBlock toolName="write_file" />);
    expect(screen.getByText("WRITE FILE")).toBeTruthy();
  });

  it("should show running state with spinner", () => {
    const { container } = render(<ToolCallBlock toolName="write_file" isRunning={true} />);
    expect(screen.getByText("WRITE FILE")).toBeTruthy();
    // Should have a spinning indicator
    expect(container.querySelector(".animate-spin")).toBeTruthy();
  });

  it("should render tool args when provided", () => {
    const args = JSON.stringify({ file_path: "/test.md", content: "hello" });
    render(<ToolCallBlock toolName="write_file" toolArgs={args} />);
    expect(screen.getByText(/test\.md/)).toBeTruthy();
  });

  it("should render result when provided (after expand)", () => {
    const { container } = render(<ToolCallBlock toolName="read_file" result="file content" />);
    // Click to expand
    const button = container.querySelector("button");
    expect(button).toBeTruthy();
    act(() => { button!.click(); });
    expect(container.textContent).toContain("file content");
  });
});
