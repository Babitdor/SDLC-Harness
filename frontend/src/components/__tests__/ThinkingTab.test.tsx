import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ThinkingTab from "../ThinkingTab";
import type { ReasoningEntry } from "../../lib/types";

describe("ThinkingTab", () => {
  it("should show empty state when no entries", () => {
    render(<ThinkingTab entries={[]} />);
    expect(screen.getByText("NO REASONING YET")).toBeTruthy();
  });

  it("should render reasoning entries", () => {
    const entries: ReasoningEntry[] = [
      { agent: "", content: "Step 1: Analyze", source: "model", ts: 1718812800000 },
    ];
    render(<ThinkingTab entries={entries} />);
    expect(screen.getByText("Step 1: Analyze")).toBeTruthy();
  });

  it("should show REASONING badge for model source", () => {
    const entries: ReasoningEntry[] = [
      { agent: "", content: "Think...", source: "model", ts: 1718812800000 },
    ];
    render(<ThinkingTab entries={entries} />);
    expect(screen.getByText("REASONING")).toBeTruthy();
  });

  it("should show PLANNING badge for planning source", () => {
    const entries: ReasoningEntry[] = [
      { agent: "", content: "Plan...", source: "planning", ts: 1718812800000 },
    ];
    render(<ThinkingTab entries={entries} />);
    expect(screen.getByText("PLANNING")).toBeTruthy();
  });

  it("should show orchestrator for empty agent", () => {
    const entries: ReasoningEntry[] = [
      { agent: "", content: "Hello", source: "model", ts: 1718812800000 },
    ];
    render(<ThinkingTab entries={entries} />);
    expect(screen.getByText("Orchestrator")).toBeTruthy();
  });

  it("should show agent name for known agents", () => {
    const entries: ReasoningEntry[] = [
      { agent: "architecture", content: "Generating ADR", source: "planning", ts: 1718812800000 },
    ];
    render(<ThinkingTab entries={entries} />);
    expect(screen.getByText("Architecture")).toBeTruthy();
  });
});
