import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import SettingsPanel from "../SettingsPanel";

// Mock the API
vi.mock("../../lib/api", () => ({
  api: {
    getModelSettings: vi.fn().mockResolvedValue({
      effective: {
        model_provider: "openai",
        reasoning_effort: "medium",
        base_url: "https://api.example.com",
        agent_model: "gpt-5",
        vision_model: "gpt-5-vision",
        retry_model: "gpt-5-mini",
      },
      api_key_set: false,
      stored: {},
    }),
    updateModelSettings: vi.fn(),
  },
}));

describe("SettingsPanel", () => {
  it("should render the Model header", () => {
    render(<SettingsPanel active={true} />);
    expect(screen.getByText("MODEL")).toBeTruthy();
  });

  it("should show loading state initially", () => {
    render(<SettingsPanel active={true} />);
    expect(screen.getByText("LOADING…")).toBeTruthy();
  });

  it("should not fetch when not active", () => {
    render(<SettingsPanel active={false} />);
    // When not active, it should not show loading
    expect(screen.queryByText("LOADING…")).toBeNull();
  });
});
