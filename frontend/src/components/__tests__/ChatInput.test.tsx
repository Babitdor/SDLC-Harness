import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ChatInput from "../ChatInput";

// Mock the API
vi.mock("../../lib/api", () => ({
  api: {
    listCustomAgents: vi.fn().mockResolvedValue({ agents: [] }),
  },
}));

describe("ChatInput", () => {
  it("should render a textarea", () => {
    render(<ChatInput onSend={vi.fn()} onUpload={vi.fn()} disabled={false} />);
    const textarea = document.querySelector("textarea");
    expect(textarea).toBeTruthy();
  });

  it("should call onSend when Enter is pressed with text", () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} onUpload={vi.fn()} disabled={false} />);

    const textarea = document.querySelector("textarea")!;
    fireEvent.change(textarea, { target: { value: "Hello" } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(onSend).toHaveBeenCalledWith("Hello");
  });

  it("should not call onSend when disabled", () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} onUpload={vi.fn()} disabled={true} />);

    const textarea = document.querySelector("textarea")!;
    fireEvent.change(textarea, { target: { value: "Hello" } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(onSend).not.toHaveBeenCalled();
  });

  it("should not send empty messages", () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} onUpload={vi.fn()} disabled={false} />);

    const textarea = document.querySelector("textarea")!;
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(onSend).not.toHaveBeenCalled();
  });

  it("should render file upload button", () => {
    render(<ChatInput onSend={vi.fn()} onUpload={vi.fn()} disabled={false} />);
    // There should be a file input
    const fileInput = document.querySelector('input[type="file"]');
    expect(fileInput).toBeTruthy();
  });

  it("should show send button", () => {
    render(<ChatInput onSend={vi.fn()} onUpload={vi.fn()} disabled={false} />);
    // The send button should be present
    const buttons = document.querySelectorAll("button");
    expect(buttons.length).toBeGreaterThan(0);
  });

  // ── Large-paste → chip ──────────────────────────────────────────────────

  const BIG = "A".repeat(1300) + "END_MARKER";

  function pasteBig(textarea: HTMLTextAreaElement, text = BIG) {
    fireEvent.paste(textarea, { clipboardData: { getData: () => text } });
  }

  it("collapses a large paste into a PASTED chip instead of the textarea", () => {
    render(<ChatInput onSend={vi.fn()} onUpload={vi.fn()} disabled={false} />);
    const textarea = document.querySelector("textarea")! as HTMLTextAreaElement;

    pasteBig(textarea);

    // Chip appears; textarea is left untouched.
    expect(screen.getByText("PASTED")).toBeTruthy();
    expect(textarea.value).toBe("");
  });

  it("does not intercept a small paste", () => {
    render(<ChatInput onSend={vi.fn()} onUpload={vi.fn()} disabled={false} />);
    const textarea = document.querySelector("textarea")! as HTMLTextAreaElement;

    pasteBig(textarea, "just a little");
    expect(screen.queryByText("PASTED")).toBeNull();
  });

  it("sends the typed message and the pasted blob combined, then clears", () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} onUpload={vi.fn()} disabled={false} />);
    const textarea = document.querySelector("textarea")! as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: "Summarize this" } });
    pasteBig(textarea);
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(onSend).toHaveBeenCalledTimes(1);
    const sent = onSend.mock.calls[0][0] as string;
    expect(sent.startsWith("Summarize this")).toBe(true);
    expect(sent).toContain("END_MARKER");
    // Chip cleared after send.
    expect(screen.queryByText("PASTED")).toBeNull();
  });

  it("opens a preview modal with the full text when the chip is clicked", () => {
    const { container } = render(
      <ChatInput onSend={vi.fn()} onUpload={vi.fn()} disabled={false} />,
    );
    const textarea = document.querySelector("textarea")! as HTMLTextAreaElement;

    pasteBig(textarea);
    // Preview snippet is truncated — the end marker isn't shown yet.
    expect(container.textContent).not.toContain("END_MARKER");

    fireEvent.click(screen.getByTitle("Click to preview pasted text"));
    // Full text is now visible in the modal.
    expect(container.textContent).toContain("END_MARKER");
  });
});
