import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ThemeToggle } from "../ThemeToggle";

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Mock matchMedia
Object.defineProperty(window, "matchMedia", {
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock document.documentElement.classList
beforeEach(() => {
  localStorageMock.clear();
  vi.clearAllMocks();
});

describe("ThemeToggle", () => {
  it("should render a button", () => {
    const { container } = render(<ThemeToggle />);
    const button = container.querySelector("button");
    expect(button).toBeTruthy();
  });

  it("should have an aria-label for accessibility", () => {
    const { container } = render(<ThemeToggle />);
    const button = container.querySelector("button");
    expect(button).toBeTruthy();
    // After mount, the button should have an aria-label
    expect(button!.getAttribute("aria-label")).toBeTruthy();
  });

  it("should toggle theme on click", () => {
    const { container } = render(<ThemeToggle />);
    const button = container.querySelector("button");
    expect(button).toBeTruthy();

    // Click to toggle
    if (button) {
      fireEvent.click(button);
      // After click, localStorage should have been updated
      expect(localStorageMock.setItem).toHaveBeenCalledWith("theme", expect.any(String));
    }
  });
});
