import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TypingIndicator from "../TypingIndicator";

describe("TypingIndicator", () => {
  it("should render the ORCHESTRATOR label", () => {
    render(<TypingIndicator />);
    expect(screen.getByText("ORCHESTRATOR")).toBeTruthy();
  });

  it("should render three typing dots", () => {
    const { container } = render(<TypingIndicator />);
    const dots = container.querySelectorAll(".typing-dot");
    expect(dots).toHaveLength(3);
  });
});
