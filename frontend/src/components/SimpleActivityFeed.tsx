"use client";

import { memo, useEffect, useState } from "react";
import { findAgent, isUnresolvedAgentName } from "../lib/agents";
import { describeToolCall } from "../lib/toolActivity";
import type { SubagentInfo, ToolCallInfo } from "../lib/types";

interface Props {
  subagents: SubagentInfo[];
}

/** Plain-English description of a subagent's current activity — the running/
 * most-recent tool in non-technical terms. */
function describeTool(toolCalls: ToolCallInfo[]): string {
  if (!toolCalls || toolCalls.length === 0) return "Thinking…";
  const active = toolCalls.find((tc) => tc.isRunning) ?? toolCalls[toolCalls.length - 1];
  return describeToolCall(active);
}

/** Collapse whitespace and cap length so a long (custom-agent) description
 * can't turn the one-line row into a wall of text. */
function short(s: string, n = 80): string {
  const t = s.trim().replace(/\s+/g, " ");
  return t.length > n ? t.slice(0, n - 1) + "…" : t;
}

/** How long a finished row stays on screen before it gets out of the way. */
const DWELL_MS = 3000;

/** Identity of one run of an agent: `completedAt` is stamped per completion. */
const runKey = (s: SubagentInfo) => `${s.name}@${s.completedAt ?? 0}`;

function SimpleActivityFeedImpl({ subagents }: Props) {
  // Names hidden once their row has had its dwell time. Rows are visible by
  // default, and the ONLY thing that removes one is the timer below — so
  // nothing can bring a removed row back.
  //
  // The previous version tracked the inverse (which names had been *seen*) and
  // paired it with an effect that re-added "any agent not in the set". That
  // effect could not tell an agent that had just arrived from one this timer
  // had deliberately hidden, so it resurrected every row the timer had just
  // removed. Because the parent rebuilt the `subagents` array on every render
  // (`page.tsx` passed `Array.from(subagents.values())` inline), the effect ran
  // on every render — so finished rows blinked out and back for as long as the
  // run kept producing output. That is the flicker.
  //
  // Entries are *runs*, not names. The map is keyed by name and accumulates
  // across a thread's turns, so the same agent gets re-invoked; dismissing by
  // name would leave its second run pre-dismissed, and the row would vanish the
  // instant that run finished, with no dwell. `completedAt` is stamped fresh on
  // every completion, so name + completedAt identifies one run.
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  // Runs eligible to be dismissed. Only *completed* ones: a failed row stays
  // until the user has seen it — that is the row they most need.
  //
  // Keyed on this derived string rather than on the `subagents` array. An
  // array identity is a new value on every render, so React would run this
  // effect's cleanup — which cancels the timer — on every streamed token, and
  // a finished row would never actually dismiss while the run was active.
  const finishedKey = subagents
    .filter((s) => s.status === "completed")
    .map(runKey)
    .sort()
    .join("|");

  useEffect(() => {
    if (!finishedKey) return;
    const runs = finishedKey.split("|");
    const timer = setTimeout(() => {
      setDismissed((prev) => {
        const next = new Set(prev);
        for (const r of runs) next.add(r);
        return next;
      });
    }, DWELL_MS);
    return () => clearTimeout(timer);
  }, [finishedKey]);

  const activeCount = subagents.filter((s) => s.status === "started").length;
  const totalCount = subagents.length;

  if (totalCount === 0) return null;

  return (
    <div>
      {/* Simple header */}
      <div className="flex items-center gap-2 mb-3">
        {activeCount > 0 ? (
          <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse flex-shrink-0" />
        ) : (
          <div className="w-2 h-2 rounded-full bg-success flex-shrink-0" />
        )}
        <span className="text-[13px] text-base-400 font-medium">
          {activeCount > 0
            ? `Working on your request…`
            : `Done (${totalCount} ${totalCount === 1 ? "step" : "steps"})`}
        </span>
      </div>

      {/* Activity rows */}
      <div className="space-y-1">
        {subagents.map((sa) => {
          // Only a completed run is ever hidden, and only the run the timer
          // dismissed — a re-invocation is a new run with a new key.
          if (sa.status === "completed" && dismissed.has(runKey(sa))) return null;

          const agent = findAgent(sa.name);
          // An unresolved namespace (e.g. "tools:<uuid>") isn't a real agent.
          // Drop it entirely when it carries nothing; otherwise show it as a
          // generic step and let the description carry what it's doing.
          const unresolved = !agent && isUnresolvedAgentName(sa.name);
          if (unresolved && !sa.toolCalls?.length && !sa.task) return null;

          const displayName = agent?.name ?? (unresolved ? "Working" : sa.name);
          // Short, non-technical label — never the raw `sa.task` (that's the
          // orchestrator's full multi-paragraph delegation instruction). While
          // running, show the live activity; otherwise the agent's role.
          const live =
            sa.status === "started" && sa.toolCalls?.length
              ? describeTool(sa.toolCalls)
              : undefined;
          const description = short(live ?? agent?.desc ?? describeTool(sa.toolCalls));

          return (
            <div
              key={sa.name}
              className={
                "flex items-center gap-3 px-3 py-2 rounded transition-all " +
                (sa.status === "started"
                  ? "bg-blue-500/[0.04]"
                  : sa.status === "completed"
                    ? "opacity-60"
                    : "opacity-60")
              }
            >
              {/* Icon */}
              <span className="w-5 h-5 flex items-center justify-center text-[13px] flex-shrink-0">
                {agent?.icon ?? "⚡"}
              </span>

              {/* Name + description */}
              <div className="flex-1 min-w-0 flex items-baseline gap-2">
                <span className="text-[13px] text-base-200 font-medium flex-shrink-0">
                  {displayName}
                </span>
                <span className="text-[12px] text-base-500 truncate">
                  {description}
                </span>
              </div>

              {/* Status indicator */}
              {sa.status === "started" ? (
                <div className="w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
              ) : sa.status === "completed" ? (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  className="text-success flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="2 7 6 11 12 3" />
                </svg>
              ) : (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  className="text-danger-400 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                >
                  <line x1="3" y1="3" x2="11" y2="11" />
                  <line x1="11" y1="3" x2="3" y2="11" />
                </svg>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const SimpleActivityFeed = memo(SimpleActivityFeedImpl);
export default SimpleActivityFeed;
