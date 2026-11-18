import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FileChips from "../FileChips";

describe("FileChips", () => {
  it("should render nothing when files array is empty", () => {
    const { container } = render(<FileChips files={[]} onRemove={vi.fn()} />);
    expect(container.innerHTML).toBe("");
  });

  it("should render file chips for each file", () => {
    const files = [
      { path: "/ws/f1.txt", originalName: "f1.txt" },
      { path: "/ws/f2.pdf", originalName: "f2.pdf" },
    ];
    render(<FileChips files={files} onRemove={vi.fn()} />);
    expect(screen.getByText("f1.txt")).toBeTruthy();
    expect(screen.getByText("f2.pdf")).toBeTruthy();
  });

  it("should call onRemove when remove button is clicked", () => {
    const onRemove = vi.fn();
    const files = [{ path: "/ws/f1.txt", originalName: "f1.txt" }];
    render(<FileChips files={files} onRemove={onRemove} />);

    const removeBtn = screen.getByText("✕");
    fireEvent.click(removeBtn);
    expect(onRemove).toHaveBeenCalledWith(0);
  });
});
