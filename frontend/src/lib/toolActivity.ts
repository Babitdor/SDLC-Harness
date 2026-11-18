import { findAgent } from "./agents";
import type { ToolCallInfo } from "./types";

// Same regex ChatMessage uses to pull the delegated subagent out of a
// streaming `task` call's JSON args.
const SUBAGENT_TYPE_RE = /"subagent_type"\s*:\s*"([^"]+)"/;

/**
 * Plain-English, non-technical description of a single tool call. The user
 * doesn't need the tool name or its arguments — just what's happening.
 * Falls back to a generic "Working…" for anything unmapped.
 */
export function describeToolCall(tc: ToolCallInfo): string {
  const name = tc.toolName;

  if (name === "task") {
    const m = tc.toolArgs?.match(SUBAGENT_TYPE_RE);
    const who = m ? (findAgent(m[1])?.name ?? m[1]) : null;
    return who ? `Delegating to ${who}…` : "Delegating a subtask…";
  }

  switch (name) {
    case "read_file":
      return "Reading files…";
    case "write_file":
      return "Writing documents…";
    case "edit_file":
      return "Updating files…";
    case "execute":
    case "shell":
    case "bash":
      return "Running analysis…";
    case "ask_question":
    case "ask_user_question":
      return "Asking a question…";
    case "grep":
    case "search":
    case "glob":
      return "Searching through files…";
    case "write_todos":
    case "todo":
      return "Planning next steps…";
    case "duckduckgo_search":
    case "web_search":
    case "web_research":
      return "Searching the web…";
    case "fetch_url":
      return "Fetching information…";
    default:
      return "Working…";
  }
}

export type ActivityState = "running" | "done" | "error";

/** Coarse status for the minimal feed — running / done / error. */
export function toolState(tc: ToolCallInfo): ActivityState {
  if (tc.isRunning && !tc.result) return "running";
  if (tc.result && (tc.result.includes("[Command failed") || tc.result.includes("Error")))
    return "error";
  return "done";
}

/**
 * Terminal cleanup for a finished run: clear `isRunning` on every tool call.
 *
 * `isRunning` is otherwise only cleared by an arriving tool_result. A tool
 * that never produces one — the run was aborted, or it errored without
 * emitting a ToolMessage — therefore keeps spinning forever on a message
 * that has already finished. `done` (or an error) means nothing further is
 * coming, so anything still marked running is finished by definition.
 *
 * The missing result is left missing rather than filled with a placeholder:
 * "ran, produced no recorded output" is the truth, and an empty string would
 * be indistinguishable from a tool that genuinely returned "".
 *
 * Returns the original array when nothing changed, so React can skip the
 * re-render.
 */
export function settleRunningToolCalls(tcs: ToolCallInfo[]): ToolCallInfo[] {
  let changed = false;
  const next = tcs.map((tc) => {
    if (!tc.isRunning) return tc;
    changed = true;
    return { ...tc, isRunning: false };
  });
  return changed ? next : tcs;
}

/**
 * Every tool-call id present in a thread's messages.
 *
 * The replay guard needs this: a run that died mid-execution is replayed by the
 * next message on the thread, re-emitting the interrupted work with **fresh
 * message ids but stable tool-call ids**. The tool id is therefore the only
 * identity that survives a restart, and it is what the stream callbacks check
 * against to avoid painting every tool call twice.
 */
export function toolIdsIn(messages: { toolCalls?: ToolCallInfo[] }[]): Set<string> {
  const ids = new Set<string>();
  for (const m of messages) {
    for (const tc of m.toolCalls || []) {
      if (tc.toolId) ids.add(tc.toolId);
    }
  }
  return ids;
}
