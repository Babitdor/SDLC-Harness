"use client";

import { memo } from "react";
import { describeToolCall, toolState, type ActivityState } from "../lib/toolActivity";
import type { ToolCallInfo } from "../lib/types";

interface Props {
  toolCalls: ToolCallInfo[];
}

interface Step {
  label: string;
  state: ActivityState;
}

/** Collapse consecutive tool calls that share the same plain-English label
 * into one step, so five `read_file`s read as a single "Reading files…". A
 * still-running call in a group keeps the whole step in the running state. */
function toSteps(toolCalls: ToolCallInfo[]): Step[] {
  const steps: Step[] = [];
  for (const tc of toolCalls) {
    const label = describeToolCall(tc);
    const state = toolState(tc);
    const last = steps[steps.length - 1];
    if (last && last.label === label) {
      if (state === "running") last.state = "running";
      else if (state === "error" && last.state !== "running") last.state = "error";
    } else {
      steps.push({ label, state });
    }
  }
  return steps;
}

function StatusIcon({ state }: { state: ActivityState }) {
  if (state === "running") {
    return (
      <div className="w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
    );
  }
  if (state === "error") {
    return (
      <svg width="14" height="14" viewBox="0 0 14 14" className="text-danger-400 flex-shrink-0"
        fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <line x1="3" y1="3" x2="11" y2="11" />
        <line x1="11" y1="3" x2="3" y2="11" />
      </svg>
    );
  }
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" className="text-success flex-shrink-0"
      fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="2 7 6 11 12 3" />
    </svg>
  );
}

/**
 * Minimal, non-technical view of what the agent is doing: a short list of
 * plain-English steps with a running/done status each. No tool names, no
 * arguments, no raw output — those live behind the "Show technical details"
 * toggle in ChatMessage.
 */
function AgentActivityImpl({ toolCalls }: Props) {
  if (!toolCalls || toolCalls.length === 0) return null;

  const steps = toSteps(toolCalls);
  const anyRunning = steps.some((s) => s.state === "running");

  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-2">
        <span
          className={
            "w-2 h-2 rounded-full flex-shrink-0 " +
            (anyRunning ? "bg-blue-400 animate-pulse" : "bg-success")
          }
        />
        <span className="text-[13px] text-base-400 font-medium">
          {anyRunning ? "Working on your request…" : "Done"}
        </span>
      </div>

      <div className="space-y-0.5">
        {steps.map((s, i) => (
          <div
            key={i}
            className={
              "flex items-center gap-3 px-3 py-1.5 rounded " +
              (s.state === "running" ? "" : "opacity-70")
            }
          >
            <StatusIcon state={s.state} />
            <span className="text-[13px] text-base-300">{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const AgentActivity = memo(AgentActivityImpl);
export default AgentActivity;
