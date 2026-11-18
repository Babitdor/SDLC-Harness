import { describe, it, expect } from "vitest";
import { settleRunningToolCalls, toolIdsIn } from "../toolActivity";
import { toArtifactPath } from "../../components/ArtifactCard";
import type { ToolCallInfo } from "../types";

const tc = (over: Partial<ToolCallInfo>): ToolCallInfo => ({
  toolId: "t1",
  toolName: "write_file",
  toolArgs: "{}",
  ...over,
});

describe("settleRunningToolCalls", () => {
  it("clears isRunning on a tool that never returned a result", () => {
    // The stuck-spinner case: isRunning is otherwise only cleared by an
    // arriving tool_result, so an aborted or errored run span forever.
    const out = settleRunningToolCalls([tc({ isRunning: true })]);
    expect(out[0].isRunning).toBe(false);
    // and does not invent a result it never had
    expect(out[0].result).toBeUndefined();
  });

  it("leaves a completed call untouched", () => {
    const done = tc({ isRunning: false, result: "ok" });
    const out = settleRunningToolCalls([done]);
    expect(out[0].result).toBe("ok");
    expect(out[0].isRunning).toBe(false);
  });

  it("preserves a result that is legitimately the empty string", () => {
    const out = settleRunningToolCalls([tc({ isRunning: true, result: "" })]);
    expect(out[0].result).toBe("");
    expect(out[0].isRunning).toBe(false);
  });

  it("returns the same array reference when nothing was running", () => {
    // Identity matters: the callers feed this straight into setState, so a
    // fresh array every time would re-render the whole transcript on every
    // done/error event.
    const input = [tc({ isRunning: false })];
    expect(settleRunningToolCalls(input)).toBe(input);
  });

  it("settles a mixed batch", () => {
    const out = settleRunningToolCalls([
      tc({ toolId: "a", isRunning: true }),
      tc({ toolId: "b", isRunning: false, result: "done" }),
      tc({ toolId: "c", isRunning: true }),
    ]);
    expect(out.map((t) => t.isRunning)).toEqual([false, false, false]);
    expect(out[1].result).toBe("done");
  });
});

describe("toolIdsIn", () => {
  it("collects the tool ids a hydrated transcript already holds", () => {
    // The replay guard compares arriving tool ids against this set. A resumed
    // run re-emits interrupted work with fresh message ids but stable
    // tool-call ids, so this is the only identity that survives a restart.
    const ids = toolIdsIn([
      { toolCalls: [tc({ toolId: "call-1" }), tc({ toolId: "call-2" })] },
      {},
      { toolCalls: [tc({ toolId: "call-3" })] },
    ]);
    expect([...ids].sort()).toEqual(["call-1", "call-2", "call-3"]);
  });

  it("is empty for a transcript with no tool calls", () => {
    expect(toolIdsIn([]).size).toBe(0);
    expect(toolIdsIn([{}, { toolCalls: [] }]).size).toBe(0);
  });

  it("skips a call with no id rather than inserting an empty key", () => {
    // An empty-string id would match every other empty-string id and suppress
    // genuine live tool calls.
    const ids = toolIdsIn([{ toolCalls: [tc({ toolId: "" }), tc({ toolId: "ok" })] }]);
    expect([...ids]).toEqual(["ok"]);
  });
});

describe("toArtifactPath", () => {
  it("strips the /workspace/current alias", () => {
    expect(toArtifactPath("/workspace/current/requirements/REQUIREMENTS.md")).toBe(
      "requirements/REQUIREMENTS.md",
    );
  });

  it("strips the real project directory the alias resolves to", () => {
    // Agents may use either form; a card must work for both.
    expect(toArtifactPath("/workspace/project_default/diagrams/bdd.mmd")).toBe(
      "diagrams/bdd.mmd",
    );
  });

  it("accepts an already-relative path", () => {
    expect(toArtifactPath("functional/ACTIVITIES.md")).toBe("functional/ACTIVITIES.md");
  });

  it("rejects scratch files outside the project", () => {
    // /tmp is where throwaway scripts are meant to go — they are not
    // deliverables and must never render as artifact cards.
    expect(toArtifactPath("/tmp/extract.py")).toBeNull();
    expect(toArtifactPath("/etc/passwd")).toBeNull();
  });

  it("rejects traversal attempts", () => {
    expect(toArtifactPath("../../etc/passwd")).toBeNull();
  });
});

// ── resume predicate (both stream entry points share it) ──────────────────

import { shouldResume } from "../../app/page";

describe("shouldResume", () => {
  const msg = (role: "user" | "assistant") =>
    ({ id: "m", role, content: "", timestamp: 0 }) as never;

  it("resumes when the thread is known to be in flight", () => {
    // switchConversation's original test.
    expect(shouldResume([msg("assistant")], "t1", new Set(["t1"]))).toBe(true);
  });

  it("resumes when the tail is not an assistant turn", () => {
    // The durable signal after a refresh, where inFlight is empty by design:
    // the backend persists the assistant turn when a run ends, so a user
    // tail means the run never finished.
    expect(shouldResume([msg("user")], "t1", new Set())).toBe(true);
  });

  it("does not resume a completed thread", () => {
    expect(shouldResume([msg("user"), msg("assistant")], "t1", new Set())).toBe(false);
  });

  it("does not resume an empty thread", () => {
    expect(shouldResume([], "t1", new Set())).toBe(false);
  });
});

// ── artifact cards must reflect the live run, not just the reloaded one ────

import { producedFiles } from "../../components/ChatMessage";

describe("producedFiles", () => {
  const write = (path: string) =>
    ({
      toolId: "t",
      toolName: "write_file",
      toolArgs: JSON.stringify({ file_path: path }),
    }) as never;

  it("finds files written directly by the orchestrator", () => {
    expect(producedFiles([write("/workspace/current/requirements/REQUIREMENTS.md")]))
      .toEqual(["requirements/REQUIREMENTS.md"]);
  });

  it("finds files written by SUBAGENTS", () => {
    // The bug: subagents do the writing, and while a run streams their
    // tool calls live on the subagent map rather than on the message. Cards
    // therefore appeared only after a refresh, when persistence merges the
    // whole run's calls onto the assistant row.
    const subagents = [
      { name: "architecture", toolCalls: [write("/workspace/current/diagrams/bdd.mmd")] },
    ] as never;
    expect(producedFiles(undefined, subagents)).toEqual(["diagrams/bdd.mmd"]);
  });

  it("merges both sources and de-duplicates", () => {
    const subagents = [
      { name: "a", toolCalls: [write("functional/ACTIVITIES.md")] },
      { name: "b", toolCalls: [write("functional/ACTIVITIES.md")] },
    ] as never;
    const out = producedFiles([write("requirements/RULES.md")], subagents);
    expect(out.sort()).toEqual(["functional/ACTIVITIES.md", "requirements/RULES.md"]);
  });

  it("ignores half-streamed args rather than rendering a broken card", () => {
    const partial = { toolId: "t", toolName: "write_file", toolArgs: '{"file_pa' } as never;
    expect(producedFiles([partial])).toEqual([]);
  });

  it("ignores scratch files outside the project", () => {
    expect(producedFiles([write("/tmp/extract.py")])).toEqual([]);
  });
});
