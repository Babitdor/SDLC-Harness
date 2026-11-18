import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import DiffPreview from "../DiffPreview";

describe("DiffPreview", () => {
  it("should render diff lines", () => {
    const { container } = render(<DiffPreview oldContent="line1\nline2" newContent="line1\nline2\nline3" />);
    // Content is rendered inside <td> elements with whitespace-pre-wrap
    expect(container.textContent).toContain("line1");
    expect(container.textContent).toContain("line2");
    expect(container.textContent).toContain("line3");
  });

  it("should show added lines", () => {
    const { container } = render(<DiffPreview oldContent="old" newContent="old\nnew" />);
    expect(container.textContent).toContain("old");
    expect(container.textContent).toContain("new");
  });

  it("should show removed lines", () => {
    render(<DiffPreview oldContent="old\nremoved" newContent="old" />);
    expect(screen.getByText("old")).toBeTruthy();
  });

  it("should render filename when provided", () => {
    render(
      <DiffPreview
        oldContent="a"
        newContent="b"
        filename="/workspace/test.md"
      />
    );
    expect(screen.getByText("/workspace/test.md")).toBeTruthy();
  });

  it("should show no-changes message for identical content", () => {
    render(<DiffPreview oldContent="same" newContent="same" />);
    expect(screen.getByText("— no changes —")).toBeTruthy();
  });
});
