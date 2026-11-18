"use client";

import { memo } from "react";
import Markdown from "./Markdown";
import { findAgent } from "../lib/agents";
import type { ReasoningEntry } from "../lib/types";

interface Props {
  entries: ReasoningEntry[];
}

/**
 * The Thinking view: a chronological feed of the fleet's reasoning —
 * native model reasoning (`source: "model"`) when available, plus the
 * client-derived planning narration (`source: "planning"`): the text an
 * agent writes just before it calls a tool. Grouped visually by agent.
 */
function ThinkingTabImpl({ entries }: Props) {
  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <span className="label-mono text-base-600">NO REASONING YET</span>
        <p className="text-[13px] text-base-500 mt-2 max-w-sm">
          The agents&apos; planning narration and any model reasoning will appear
          here as they work.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 px-1 py-2">
      {entries.map((e, i) => {
        const agent = e.agent ? findAgent(e.agent) : undefined;
        const who = e.agent ? agent?.name ?? e.agent : "Orchestrator";
        return (
          <div
            key={i}
            className="border border-base-800 bg-base-900/30 px-4 py-3 tick-corners"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="w-5 h-5 border border-cyan-500/40 bg-cyan-500/5 flex items-center justify-center text-[11px] flex-shrink-0">
                {agent?.icon ?? <span className="font-mono text-cyan-300">@</span>}
              </span>
              <span className="font-display text-[13px] text-base-200 italic flex-1 truncate">
                {who}
              </span>
              <span
                className={
                  "label-mono " +
                  (e.source === "model" ? "text-cyan-400" : "text-base-500")
                }
              >
                {e.source === "model" ? "REASONING" : "PLANNING"}
              </span>
            </div>
            <div className="text-[13px] text-base-300 leading-relaxed">
              <Markdown content={e.content} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

const ThinkingTab = memo(ThinkingTabImpl);
export default ThinkingTab;
