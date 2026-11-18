import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import SimpleActivityFeed from "../SimpleActivityFeed";
import type { SubagentInfo } from "../../lib/types";

// ── Why this file exists ────────────────────────────────────────────────
// The feed shows a finished row for a dwell period, then gets it out of the
// way. It used to track which names it had *seen* and run a second effect that
// re-added "any agent not in that set". That effect cannot tell an agent which
// has just arrived from one the dwell timer deliberately hid, so it brought
// the row back; the timer then hid it again three seconds later. The parent
// rebuilds `subagents` on every render (`Array.from(subagents.values())`), so
// the effect fired on every render and finished rows blinked continuously for
// as long as the run produced output.
//
// These tests pin the invariant: the dwell timer is the ONLY thing that
// removes a row, so no amount of re-rendering can bring one back.
// ────────────────────────────────────────────────────────────────────────

const DWELL_MS = 3000;

/**
 * A fixture name that resolves to no registered agent and is not an unresolved
 * namespace (`isUnresolvedAgentName` only matches `tools:` and uuid shapes), so
 * the row renders its own name and the queries below are unambiguous.
 */
const sa = (over: Partial<SubagentInfo> = {}): SubagentInfo => ({
  name: "alpha-agent",
  path: ["/workspace"],
  status: "completed",
  messages: [],
  toolCalls: [],
  startedAt: 0,
  ...over,
});

describe("SimpleActivityFeed row lifetime", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not resurrect a dismissed row when the parent re-renders", async () => {
    const { rerender } = render(
      <SimpleActivityFeed subagents={[sa({ name: "alpha-agent" })]} />,
    );
    expect(screen.getByText("alpha-agent")).toBeTruthy();

    await act(async () => {
      vi.advanceTimersByTime(DWELL_MS);
    });
    expect(screen.queryByText("alpha-agent")).toBeNull();

    // Same content, fresh array identity — exactly what a streamed token
    // causes in page.tsx. The row must stay gone.
    rerender(<SimpleActivityFeed subagents={[sa({ name: "alpha-agent" })]} />);
    expect(screen.queryByText("alpha-agent")).toBeNull();

    // Repeat: a resurrection that only appears on a later pass would be missed
    // by asserting once.
    for (let i = 0; i < 3; i++) {
      rerender(<SimpleActivityFeed subagents={[sa({ name: "alpha-agent" })]} />);
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });
      expect(screen.queryByText("alpha-agent")).toBeNull();
    }
  });

  it("unrelated activity must not revive an already-dismissed row", async () => {
    // The strongest form of the bug: one agent finishing and being dismissed,
    // then a DIFFERENT agent flowing through the list. That is the ordinary
    // shape of a multi-agent run, and it is what made the flicker look random.
    const { rerender } = render(
      <SimpleActivityFeed subagents={[sa({ name: "alpha-agent" })]} />,
    );
    await act(async () => {
      vi.advanceTimersByTime(DWELL_MS);
    });
    expect(screen.queryByText("alpha-agent")).toBeNull();

    rerender(
      <SimpleActivityFeed
        subagents={[sa({ name: "alpha-agent" }), sa({ name: "beta-agent", status: "started" })]}
      />,
    );
    expect(screen.queryByText("alpha-agent")).toBeNull();
    expect(screen.getByText("beta-agent")).toBeTruthy();

    // beta finishes too. The dwell timer is armed when the set of finished
    // agents changes, so it starts counting from here.
    rerender(
      <SimpleActivityFeed
        subagents={[sa({ name: "alpha-agent" }), sa({ name: "beta-agent" })]}
      />,
    );
    await act(async () => {
      vi.advanceTimersByTime(DWELL_MS);
    });

    // Neither row may come back from the dead, on this render or the next.
    expect(screen.queryByText("alpha-agent")).toBeNull();
    expect(screen.queryByText("beta-agent")).toBeNull();
    rerender(
      <SimpleActivityFeed
        subagents={[sa({ name: "alpha-agent" }), sa({ name: "beta-agent" })]}
      />,
    );
    expect(screen.queryByText("alpha-agent")).toBeNull();
    expect(screen.queryByText("beta-agent")).toBeNull();
  });

  it("dismisses a finished row once, and not before the dwell time", async () => {
    render(<SimpleActivityFeed subagents={[sa({ name: "beta-agent" })]} />);

    await act(async () => {
      vi.advanceTimersByTime(DWELL_MS - 1);
    });
    expect(screen.getByText("beta-agent")).toBeTruthy();

    await act(async () => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.queryByText("beta-agent")).toBeNull();
  });

  it("shows an agent again when it is invoked a second time", async () => {
    // The map is keyed by name and accumulates across a thread's turns, so the
    // same agent being invoked again is a re-invocation, not a new row. A
    // dismissed name must not hide its whole second run.
    // `completedAt` is stamped on every completion (onSubagentCompleted), so
    // each run carries its own value — as it does in the app.
    const { rerender } = render(
      <SimpleActivityFeed subagents={[sa({ name: "alpha-agent", completedAt: 1000 })]} />,
    );
    await act(async () => {
      vi.advanceTimersByTime(DWELL_MS);
    });
    expect(screen.queryByText("alpha-agent")).toBeNull();

    rerender(
      <SimpleActivityFeed subagents={[sa({ name: "alpha-agent", status: "started" })]} />,
    );
    expect(screen.getByText("alpha-agent")).toBeTruthy();

    // The second run finishes: it gets the full dwell like any other row. The
    // first run's dismissal must not carry over and hide it instantly.
    rerender(
      <SimpleActivityFeed subagents={[sa({ name: "alpha-agent", completedAt: 2000 })]} />,
    );
    expect(screen.getByText("alpha-agent")).toBeTruthy();

    await act(async () => {
      vi.advanceTimersByTime(DWELL_MS);
    });
    expect(screen.queryByText("alpha-agent")).toBeNull();
  });

  it("keeps a failed row on screen", async () => {
    // Only completed runs are dismissed. A failure is the row the user most
    // needs to see, so it must not disappear on the dwell timer.
    render(<SimpleActivityFeed subagents={[sa({ name: "alpha-agent", status: "failed" })]} />);
    await act(async () => {
      vi.advanceTimersByTime(DWELL_MS * 2);
    });
    expect(screen.getByText("alpha-agent")).toBeTruthy();
  });

  it("never hides a row that is still running", async () => {
    render(
      <SimpleActivityFeed subagents={[sa({ name: "gamma-agent", status: "started" })]} />,
    );

    await act(async () => {
      vi.advanceTimersByTime(60_000);
    });
    expect(screen.getByText("gamma-agent")).toBeTruthy();
  });
});
