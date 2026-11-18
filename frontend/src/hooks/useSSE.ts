"use client";

import { useCallback, useRef, useState } from "react";
import type { SSEEvent, TodoItemInfo } from "../lib/types";

export interface UseSSEOptions {
  onToken: (token: string, agent?: string) => void;
  onToolCall?: (event: { toolName: string; toolArgs: string; toolId: string; agent?: string }) => void;
  onToolArgs?: (event: { toolName: string; toolId: string; content: string; agent?: string }) => void;
  onToolResult?: (event: { toolName: string; toolId: string; content: string; agent?: string }) => void;
  onSubagentStarted?: (event: { agent: string; path: string[]; task?: string }) => void;
  onSubagentCompleted?: (event: { agent: string; path: string[] }) => void;
  onSubagentFailed?: (event: { agent: string; path: string[] }) => void;
  onValues?: (event: { todos?: Array<{ content: string; status: string }>; agent?: string }) => void;
  /** A todo list (orchestrator if agent==="", else that subagent's). */
  onTodos?: (event: { agent: string; items: TodoItemInfo[] }) => void;
  /** A reasoning/thinking chunk (native model output). */
  onReasoning?: (event: { agent: string; content: string; source: "model" | "planning" }) => void;
  onDone: (traceUrl?: string, subagents?: Array<{ name: string; path: string[] }>) => void;
  onError: (detail: string) => void;
}

/**
 * Dispatch one parsed SSE event to the right callback. Used by both
 * `send()` (the initial POST /chat/stream consumer) and `subscribe()`
 * (the GET /chat/resume re-attach consumer) so event-type → callback
 * routing lives in exactly one place.
 */
function dispatchSSEEvent(event: SSEEvent, opts: UseSSEOptions) {
  switch (event.type) {
    case "token":
      if (event.content) opts.onToken(event.content, event.agent);
      break;
    case "tool_call":
      opts.onToolCall?.({
        toolName: event.tool_name || "",
        toolArgs: event.tool_args || "",
        toolId: event.tool_id || "",
        agent: event.agent,
      });
      break;
    case "tool_args":
      opts.onToolArgs?.({
        toolName: event.tool_name || "",
        toolId: event.tool_id || "",
        content: event.content || "",
        agent: event.agent,
      });
      break;
    case "tool_result":
      opts.onToolResult?.({
        toolName: event.tool_name || "",
        toolId: event.tool_id || "",
        content: event.content || "",
        agent: event.agent,
      });
      break;
    case "subagent_started":
      opts.onSubagentStarted?.({
        agent: event.agent || "unknown",
        path: event.path || [],
        task: event.task,
      });
      break;
    case "subagent_completed":
      opts.onSubagentCompleted?.({
        agent: event.agent || "unknown",
        path: event.path || [],
      });
      break;
    case "subagent_failed":
      opts.onSubagentFailed?.({
        agent: event.agent || "unknown",
        path: event.path || [],
      });
      break;
    case "todos":
      if (event.items) {
        opts.onTodos?.({ agent: event.agent || "", items: event.items });
      }
      break;
    case "reasoning":
      if (event.content) {
        opts.onReasoning?.({
          agent: event.agent || "",
          content: event.content,
          source: event.source || "model",
        });
      }
      break;
    case "done":
      opts.onDone(event.trace_url, event.subagents);
      break;
    case "run_started":
      // Informational. A resumed run replays the interrupted work with fresh
      // message ids, so `_seq` (which restarts at 1 each run) cannot identify
      // it; the backend marks it here. The replay guard in page.tsx is what
      // acts on it — suppressing a duplicate here would be wrong, because the
      // same events also have to reach a client that has no transcript yet.
      if (event.resume) {
        console.debug(
          `[useSSE] resumed run: replaying ${event.replayed ?? 0} prior item(s)`,
        );
      }
      break;
    case "values":
      opts.onValues?.({
        todos: event.todos,
        agent: event.agent,
      });
      break;
    case "error":
      opts.onError(event.detail || "Unknown error");
      break;
  }
}

/**
 * Drive an SSE stream from a fetch response's body reader: decode UTF-8,
 * split on newlines, parse each `data: …` line, dispatch to callbacks.
 * Used by both `send()` (the initial /chat/stream POST consumer) and
 * `subscribe()` (the /chat/resume GET re-attach consumer). The two
 * differ only in HTTP method + body — once the reader is in hand the
 * parsing is identical.
 */
async function consumeSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  opts: UseSSEOptions,
  /**
   * Highest run-sequence already applied for this thread, carried across
   * reconnects. The backend replays a run's entire history to every new
   * subscriber, so without this a re-attach paints the run's output a
   * second time. Mutated in place so the caller keeps the mark when this
   * stream ends.
   */
  seen?: { seq: number },
) {
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data:")) continue;
      const raw = line.substring(5).trim();
      if (!raw) continue;
      try {
        const event: SSEEvent = JSON.parse(raw);
        if (seen && typeof event._seq === "number") {
          if (event._seq <= seen.seq) continue; // replayed — already applied
          seen.seq = event._seq;
        }
        dispatchSSEEvent(event, opts);
      } catch (e) {
        console.error("SSE JSON.parse error:", e, "Raw string:", raw);
        // Skip malformed JSON — usually a partial chunk that completes next read
      }
    }
  }

  // Drain any trailing buffer (last event without a newline terminator)
  if (buffer.startsWith("data:")) {
    const raw = buffer.substring(5).trim();
    if (raw) {
      try {
        const event: SSEEvent = JSON.parse(raw);
        if (seen && typeof event._seq === "number") {
          if (event._seq > seen.seq) {
            seen.seq = event._seq;
            dispatchSSEEvent(event, opts);
          }
        } else {
          dispatchSSEEvent(event, opts);
        }
      } catch (e) {
        console.error("SSE trailing JSON.parse error:", e, "Raw string:", raw);
        /* ignore */
      }
    }
  }
}

export function useSSE() {
  /**
   * Which threads currently hold an open stream.
   *
   * This was a single boolean, which could only ever describe the thread on
   * screen — so a background run either had to be torn down on every switch
   * or misreport the visible thread as busy. A set lets several runs be live
   * at once and lets the UI ask about a specific thread.
   */
  const [streamingThreads, setStreamingThreads] = useState<Set<string>>(new Set());

  const markStreaming = useCallback((threadId: string, on: boolean) => {
    setStreamingThreads((prev) => {
      if (prev.has(threadId) === on) return prev; // no-op: skip the re-render
      const next = new Set(prev);
      if (on) next.add(threadId);
      else next.delete(threadId);
      return next;
    });
  }, []);

  /**
   * One abort controller PER THREAD.
   *
   * A single shared controller meant every new stream tore down whichever
   * one was already open, so switching threads necessarily stopped watching
   * the run you were leaving. Keyed per thread, streams are independent:
   * starting one on thread B leaves thread A's alone.
   */
  const abortRef = useRef<Map<string, AbortController>>(new Map());

  /**
   * Highest run-sequence applied per thread, kept across reconnects so a
   * re-attach can discard the replayed prefix instead of painting it twice.
   *
   * SCOPED TO A RUN, NOT TO A THREAD. The backend numbers events from 1
   * within each run — a new `POST /chat/stream` builds a fresh RunContext —
   * so a mark left over from the previous run is numerically higher than
   * every event of the next one. This is what silently ate a follow-up
   * message: no tokens, no `done`, WORKING chip stuck. `send()` therefore
   * clears the mark before consuming, because it always starts a new run.
   * `subscribe()` deliberately does not: its replay is the *same* run's
   * prefix, and the mark is the only thing that identifies it as a replay.
   *
   * Also cleared via `forgetThreadSeq` whenever the UI throws that thread's
   * message state away (switching threads reloads from postgres), because
   * the replay is then the only source of the in-flight run's output and
   * must be applied in full.
   */
  const seenSeqRef = useRef<Map<string, { seq: number }>>(new Map());

  const markerFor = useCallback((threadId: string) => {
    let m = seenSeqRef.current.get(threadId);
    if (!m) {
      m = { seq: -1 };
      seenSeqRef.current.set(threadId, m);
    }
    return m;
  }, []);

  const forgetThreadSeq = useCallback((threadId: string) => {
    seenSeqRef.current.delete(threadId);
  }, []);

  /**
   * Stop one thread's stream, or every stream when called with no argument.
   *
   * Switching threads no longer aborts anything — the outgoing run keeps
   * streaming into its own state slot. This is for genuine cancellation:
   * the Stop button, deleting a thread, or unmount.
   */
  const abort = useCallback(
    (threadId?: string) => {
      if (threadId === undefined) {
        for (const c of abortRef.current.values()) c.abort();
        abortRef.current.clear();
        setStreamingThreads(new Set());
        return;
      }
      abortRef.current.get(threadId)?.abort();
      abortRef.current.delete(threadId);
      markStreaming(threadId, false);
    },
    [markStreaming],
  );

  /** Is a stream already open for this thread? Guards double-subscribing. */
  const isStreaming = useCallback(
    (threadId: string) => abortRef.current.has(threadId),
    [],
  );

  const send = useCallback(
    async (
      message: string,
      threadId: string,
      projectId: string,
      uploadedFiles: string[],
      fileNames: string[],
      opts: UseSSEOptions
    ) => {
      abort(threadId);
      // A POST always starts a NEW run on the backend, whose event numbering
      // restarts at 1. Keep the previous run's high-water mark and every event
      // of this run compares as a replay and is dropped — including `done`,
      // which leaves the UI on WORKING with its spinners still turning.
      //
      // Not routed through `forgetThreadSeq` only to avoid widening this
      // callback's dep array; it is the same clear of the same ref.
      // `subscribe()` must NOT do this: its replay is the SAME run's prefix,
      // and the mark is the only thing that identifies it as a replay.
      seenSeqRef.current.delete(threadId);
      const controller = new AbortController();
      abortRef.current.set(threadId, controller);
      markStreaming(threadId, true);

      try {
        const res = await fetch("http://localhost:8000/chat/stream", {
          // The session is an HttpOnly cookie; without this the stream 401s.
          credentials: "include",
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message,
            thread_id: threadId,
            project_id: projectId,
            uploaded_files: uploadedFiles,
            file_names: fileNames,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const text = await res.text();
          opts.onError("HTTP " + res.status + ": " + text);
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) {
          opts.onError("No response body");
          return;
        }

        await consumeSSEStream(reader, opts, markerFor(threadId));
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        opts.onError(err instanceof Error ? err.message : String(err));
      } finally {
        markStreaming(threadId, false);
        if (abortRef.current.get(threadId) === controller) {
          abortRef.current.delete(threadId);
        }
      }
    },
    [abort]
  );

  /**
   * Re-attach to an in-flight (or recently-finished) agent run.
   *
   * Calls GET /chat/resume?thread_id=X which replays the run's event
   * history so far and then tails live events until the runner finishes.
   * Same callbacks as `send()` so the chat UI repaints subagent cards,
   * tool blocks, and streaming tokens identically — the user sees the
   * in-progress state instead of a blank thread.
   *
   * If no run is in-flight for the given thread, the backend returns an
   * empty stream that closes immediately; the caller's `onDone` (or
   * stream-close handling) decides what to do next (typically refetch
   * `listMessages` to grab the persisted assistant turn).
   */
  const subscribe = useCallback(
    async (threadId: string, opts: UseSSEOptions) => {
      abort(threadId);
      const controller = new AbortController();
      abortRef.current.set(threadId, controller);
      markStreaming(threadId, true);

      try {
        const res = await fetch(
          `http://localhost:8000/chat/resume?thread_id=${encodeURIComponent(threadId)}`,
          { credentials: "include", method: "GET", signal: controller.signal },
        );

        if (!res.ok) {
          const text = await res.text();
          opts.onError("HTTP " + res.status + ": " + text);
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) {
          opts.onError("No response body");
          return;
        }

        await consumeSSEStream(reader, opts, markerFor(threadId));
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        opts.onError(err instanceof Error ? err.message : String(err));
      } finally {
        markStreaming(threadId, false);
        if (abortRef.current.get(threadId) === controller) {
          abortRef.current.delete(threadId);
        }
      }
    },
    [abort]
  );

  return { streamingThreads, isStreaming, send, subscribe, abort, forgetThreadSeq };
}
