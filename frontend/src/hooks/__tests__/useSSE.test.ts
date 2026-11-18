import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSSE, type UseSSEOptions } from "../useSSE";

// ── Why this file exists ────────────────────────────────────────────────
// The backend numbers SSE events from 1 *within each run*: every
// POST /chat/stream builds a fresh RunContext. The client's dedup mark,
// though, is keyed per THREAD. Left alone, the second message in a thread is
// numbered 1..N while the mark still holds the first run's token count, so
// every event — `done` included — compares as a replay and is dropped. The UI
// then shows nothing at all and stays on WORKING with its spinners turning.
//
// These tests pin the invariant that fixes it: `send()` starts a run and so
// clears the mark; `subscribe()` re-attaches to the *same* run and must not.
// ────────────────────────────────────────────────────────────────────────

const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

const enc = new TextEncoder();

/**
 * A stand-in for a fetch response carrying an SSE body.
 *
 * Deliberately a duck-typed reader rather than a real `ReadableStream`:
 * `consumeSSEStream` only ever calls `getReader().read()`, and jsdom does not
 * implement Streams, so depending on one would test the environment instead of
 * the hook.
 */
function sseResponse(events: Array<Record<string, unknown>>) {
  const text = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
  const chunks = [text];
  let i = 0;
  return {
    ok: true,
    body: {
      getReader: () => ({
        read: async () =>
          i < chunks.length
            ? { done: false, value: enc.encode(chunks[i++]) }
            : { done: true, value: undefined },
      }),
    },
  };
}

function mkOpts(over: Partial<UseSSEOptions> = {}): UseSSEOptions {
  return {
    onToken: () => {},
    onDone: () => {},
    onError: () => {},
    ...over,
  };
}

/** Collect tokens + done-calls for one run, as the chat UI would. */
function recorder() {
  const tokens: string[] = [];
  const done = vi.fn();
  const errors: string[] = [];
  return {
    tokens,
    done,
    errors,
    opts: (over: Partial<UseSSEOptions> = {}) =>
      mkOpts({
        onToken: (t: string) => tokens.push(t),
        onDone: done,
        onError: (d: string) => errors.push(d),
        ...over,
      }),
  };
}

describe("useSSE — event numbering is scoped to a run, not a thread", () => {
  it("applies a second run's events even though its numbering restarts at 1", async () => {
    const { result } = renderHook(() => useSSE());

    // Run 1 — a long answer, so its high-water mark ends at 4.
    mockFetch.mockResolvedValueOnce(
      sseResponse([
        { type: "token", content: "one ", _seq: 1 },
        { type: "token", content: "two ", _seq: 2 },
        { type: "token", content: "three", _seq: 3 },
        { type: "done", _seq: 4 },
      ]),
    );
    const first = recorder();
    await act(async () => {
      await result.current.send("first", "t1", "p1", [], [], first.opts());
    });
    expect(first.tokens.join("")).toBe("one two three");
    expect(first.done).toHaveBeenCalled();

    // Run 2 on the SAME thread — numbering starts at 1 again. This is the
    // regression: every one of these events used to be discarded, `done`
    // included, so the follow-up message produced no output at all.
    mockFetch.mockResolvedValueOnce(
      sseResponse([
        { type: "token", content: "NEW", _seq: 1 },
        { type: "done", _seq: 2 },
      ]),
    );
    const second = recorder();
    await act(async () => {
      await result.current.send("second", "t1", "p1", [], [], second.opts());
    });

    expect(second.tokens.join("")).toBe("NEW");
    expect(second.done).toHaveBeenCalled();
    expect(second.errors).toEqual([]);
  });

  it("still discards a re-attach's replayed prefix", async () => {
    // The other half of the invariant. `subscribe()` tails the run that is
    // still in flight, and the backend replays that run's whole history to
    // every new subscriber — the mark is the only thing that identifies the
    // prefix as a replay. Resetting it here would double-paint the run.
    const { result } = renderHook(() => useSSE());

    mockFetch.mockResolvedValueOnce(
      sseResponse([
        { type: "token", content: "old ", _seq: 1 },
        { type: "token", content: "news", _seq: 2 },
        { type: "done", _seq: 3 },
      ]),
    );
    const first = recorder();
    await act(async () => {
      await result.current.send("first", "t1", "p1", [], [], first.opts());
    });
    expect(first.tokens.join("")).toBe("old news");

    // Re-attach: seq 1..3 are the same run's history (already applied), seq 4
    // is genuinely new output.
    mockFetch.mockResolvedValueOnce(
      sseResponse([
        { type: "token", content: "old ", _seq: 1 },
        { type: "token", content: "news", _seq: 2 },
        { type: "done", _seq: 3 },
        { type: "token", content: "LIVE", _seq: 4 },
      ]),
    );
    const resumed = recorder();
    await act(async () => {
      await result.current.subscribe("t1", resumed.opts());
    });

    expect(resumed.tokens.join("")).toBe("LIVE");
  });

  it("does not let a mark from one thread suppress another thread's first run", async () => {
    const { result } = renderHook(() => useSSE());

    mockFetch.mockResolvedValueOnce(
      sseResponse([
        { type: "token", content: "a a a a a", _seq: 1 },
        { type: "done", _seq: 2 },
      ]),
    );
    const a = recorder();
    await act(async () => {
      await result.current.send("msg", "threadA", "p1", [], [], a.opts());
    });

    mockFetch.mockResolvedValueOnce(
      sseResponse([
        { type: "token", content: "b", _seq: 1 },
        { type: "done", _seq: 2 },
      ]),
    );
    const b = recorder();
    await act(async () => {
      await result.current.send("msg", "threadB", "p1", [], [], b.opts());
    });

    expect(a.tokens.join("")).toBe("a a a a a");
    expect(b.tokens.join("")).toBe("b");
    expect(b.done).toHaveBeenCalled();
  });
});
