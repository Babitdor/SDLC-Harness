import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TodoList, { extractTodoList } from "../TodoList";

describe("extractTodoList", () => {
  it("should extract todo items from Python-style dicts", () => {
    const content = 'Updated todo list to [{"content": "Fix bug", "status": "in_progress"}]';
    const result = extractTodoList(content);
    expect(result).not.toBeNull();
    expect(result!.items).toHaveLength(1);
    expect(result!.items[0].content).toBe("Fix bug");
    expect(result!.items[0].status).toBe("in_progress");
  });

  it("should extract todo items from single-quote dicts", () => {
    const content = "Updated todo list to [{'content': 'Fix bug', 'status': 'in_progress'}]";
    const result = extractTodoList(content);
    expect(result).not.toBeNull();
    expect(result!.items).toHaveLength(1);
  });

  it("should return null for content without todo list", () => {
    const result = extractTodoList("Hello world");
    expect(result).toBeNull();
  });

  it("should return null for empty content", () => {
    expect(extractTodoList("")).toBeNull();
  });

  it("should extract before and after text", () => {
    const content = 'Before text. Updated todo list to [{"content": "Task 1", "status": "completed"}]. After text.';
    const result = extractTodoList(content);
    expect(result).not.toBeNull();
    expect(result!.before).toContain("Before text");
    expect(result!.after).toContain("After text");
  });

  it("should extract multiple todo items", () => {
    const content = 'Updated todo list to [{"content": "Task 1", "status": "completed"}, {"content": "Task 2", "status": "in_progress"}]';
    const result = extractTodoList(content);
    expect(result).not.toBeNull();
    expect(result!.items).toHaveLength(2);
  });
});

describe("TodoList", () => {
  it("should render todo items with status", () => {
    const items = [
      { content: "Task 1", status: "completed" as const },
      { content: "Task 2", status: "in_progress" as const },
      { content: "Task 3", status: "pending" as const },
    ];
    render(<TodoList items={items} />);
    expect(screen.getByText("Task 1")).toBeTruthy();
    expect(screen.getByText("Task 2")).toBeTruthy();
    expect(screen.getByText("Task 3")).toBeTruthy();
  });

  it("should render empty list gracefully", () => {
    const { container } = render(<TodoList items={[]} />);
    expect(container.innerHTML).toBeTruthy();
  });
});
