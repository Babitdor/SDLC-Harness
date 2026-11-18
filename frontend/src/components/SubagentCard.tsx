"use client";

import { memo, useEffect, useState } from "react";
import Markdown from "./Markdown";
import ToolCallBlock from "./ToolCallBlock";
import TodoList from "./TodoList";
import { findAgent, isUnresolvedAgentName } from "../lib/agents";
import { describeToolCall } from "../lib/toolActivity";
import type { SubagentInfo } from "../lib/types";

interface Props {
  subagent: SubagentInfo;
}

function getElapsedTime(startedAt?: number, completedAt?: number): string | null {
  if (!startedAt) return null;
  const end = completedAt ?? Date.now();
  const seconds = Math.round((end - startedAt) / 1000);
  if (seconds < 1) return "<1S";
  if (seconds < 60) return `${seconds}S`;
  return `${Math.floor(seconds / 60)}M${(seconds % 60).toString().padStart(2, "0")}`;
}

function SubagentCardImpl({ subagent }: Props) {
  const { name, status, messages, toolCalls, task, todos, startedAt, completedAt } = subagent;
  // Map the backend's lowercase agent name ("architecture") to its proper
  // display form ("Architecture") plus icon and phase. Falls back to the raw
  // name if the agent isn't in the roster (e.g. unresolved "tools:UUID").
  const agent = findAgent(name);
  // An unresolved namespace ("tools:<uuid>") isn't a real agent — label the
  // card by what it's actually doing (its running/last tool) instead of the
  // raw id, so the technical view stays legible too.
  const unresolved = !agent && isUnresolvedAgentName(name);
  const activeTc =
    toolCalls.find((t) => t.isRunning) ?? toolCalls[toolCalls.length - 1];
  const displayName =
    agent?.name ??
    (unresolved ? (activeTc ? describeToolCall(activeTc) : "Working") : name);

  // Auto-collapse completed cards after 3s — they're "filed" once done.
  const [expanded, setExpanded] = useState(status !== "completed");

  useEffect(() => {
    if (status === "completed") {
      const timer = setTimeout(() => setExpanded(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [status]);

  // Tick once per second while running, for elapsed time.
  const [, setTick] = useState(0);
  useEffect(() => {
    if (status !== "started") return;
    const interval = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(interval);
  }, [status]);

  const elapsed = getElapsedTime(startedAt, completedAt);

  // Status badge per status.
  const statusBlock =
    status === "started" ? (
      <span className="label-mono text-blue-300">RUNNING</span>
    ) : status === "completed" ? (
      <span className="label-mono text-success">COMPLETE</span>
    ) : (
      <span className="label-mono text-danger-400">FAILED</span>
    );

  return (
    <div className="border border-base-700 bg-base-900/40 relative">
      {/* Header — instrument plate */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-base-800/40 transition-colors group"
      >
        {/* Agent sigil — icon if known, @ as fallback */}
        <span className="w-6 h-6 border border-blue-400/30 bg-blue-400/5 flex items-center justify-center text-[12px] flex-shrink-0">
          {agent?.icon ?? <span className="font-mono text-blue-300">@</span>}
        </span>
        <span className="flex flex-col flex-1 min-w-0">
          <span className="text-[14px] text-base-100 font-medium truncate">
            {displayName}
          </span>
          {task && (
            <span className="text-[12px] text-base-400 truncate" title={task}>
              ▸ {task}
            </span>
          )}
        </span>
        {agent && (
          <span data-phase={agent.phase} className="phase-code flex-shrink-0">
            P{agent.phase.toString().padStart(2, "0")}
          </span>
        )}
        <div className="flex items-center gap-3 flex-shrink-0">
          {elapsed && (
            <span className="label-mono text-base-500 tabular-nums">{elapsed}</span>
          )}
          <div className="flex items-center gap-2">
            {statusBlock}
          </div>
          <svg
            className={
              "w-3 h-3 text-base-500 transition-transform group-hover:text-blue-300 " +
              (expanded ? "rotate-180" : "")
            }
            viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>
      </button>

      {/* Body */}
      {expanded && (
        <div className="border-t border-base-700 px-4 py-3 bg-base-950/30 space-y-3">
          {todos && todos.length > 0 && <TodoList items={todos} />}

          {messages.length === 0 && toolCalls.length === 0 && status === "started" && (
            <div className="flex items-center gap-3 py-1">
              <div className="w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin" />
              <span className="label-mono text-blue-400/80">WORKING</span>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className="text-[14px] text-base-200 leading-relaxed">
              <Markdown content={msg.content} />
            </div>
          ))}

          {toolCalls.map((tc, i) => (
            <ToolCallBlock
              key={`${tc.toolId || i}`}
              toolName={tc.toolName || "Tool"}
              toolArgs={tc.toolArgs}
              result={tc.result}
              isRunning={tc.isRunning}
            />
          ))}

          {messages.length === 0 && toolCalls.length === 0 && status === "completed" && (
            <p className="label-mono text-base-600 italic">TASK COMPLETED · NO OUTPUT MESSAGES</p>
          )}
        </div>
      )}
    </div>
  );
}

// Memoized so a token arriving for one subagent doesn't re-render the
// cards for every other subagent.
const SubagentCard = memo(SubagentCardImpl);
export default SubagentCard;
