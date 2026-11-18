"use client";

import { useEffect, useRef } from "react";
import type { AgentInfo } from "../lib/agents";

interface Props {
  /** Already-filtered list of agents to display. ChatInput owns the
   * filtering logic so built-ins and custom agents apply the same rules. */
  items: AgentInfo[];
  activeIndex: number;
  onSelect: (name: string) => void;
  visible: boolean;
}

export default function MentionDropdown({ items, activeIndex, onSelect, visible }: Props) {
  // Refs for keyboard-driven scroll-into-view (avoids the user navigating
  // to an item that's been scrolled off the visible portion of the list).
  const listRef = useRef<HTMLUListElement>(null);
  const activeItemRef = useRef<HTMLLIElement>(null);

  useEffect(() => {
    if (!visible) return;
    activeItemRef.current?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, visible]);

  if (!visible) return null;
  if (items.length === 0) return null;

  // The positioning wrapper is intentionally a separate element from the
  // styled panel. The visual styles include `tick-corners`, which sets
  // `position: relative` in globals.css — that fights with Tailwind's
  // `absolute` when both land on the same node. Splitting them guarantees
  // the dropdown anchors to the composer's top edge via `bottom-full`,
  // instead of flowing into normal document order halfway up the page.
  return (
    <div
      className="absolute bottom-full left-6 right-6 mb-3 z-50 pointer-events-none"
      style={{ position: "absolute" }}
    >
      <div className="pointer-events-auto bg-base-900 border border-base-600 min-w-[300px] max-w-md tick-corners max-h-[60vh] flex flex-col shadow-lg shadow-base-950/50">
        {/* Header row — drafting binder label */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-base-700 flex-shrink-0">
          <span className="label-mono text-blue-500/80">SUMMON</span>
          <div className="flex-1 h-px bg-base-700" />
          <span className="label-mono text-base-600 tabular-nums">
            {items.length.toString().padStart(2, "0")}
          </span>
        </div>

        <ul ref={listRef} className="overflow-y-auto">
          {items.map((s, i) => {
            const active = i === activeIndex;
            return (
              <li key={s.name} ref={active ? activeItemRef : null}>
                <button
                  className={
                    "group w-full flex items-center gap-3 px-3 py-2 text-left border-l-2 transition-all " +
                    (active
                      ? "border-blue-500 bg-blue-500/[0.08]"
                      : "border-transparent hover:border-base-500 hover:bg-base-800/40")
                  }
                  onMouseDown={(e) => {
                    // Prevent textarea blur — otherwise the dropdown closes
                    // before the click handler fires.
                    e.preventDefault();
                    onSelect(s.name);
                  }}
                >
                  {/* Phase plate — mono number for built-ins, CUSTOM badge
                      for user-created subagents. Same hairline frame so the
                      list reads as one continuous roster. */}
                  <span
                    className={
                      "label-mono px-1.5 py-1 border tabular-nums flex-shrink-0 " +
                      (active
                        ? "border-blue-500/60 text-blue-300"
                        : s.custom
                          ? "border-blue-500/30 text-blue-500/80"
                          : "border-base-700 text-base-500 group-hover:text-base-300")
                    }
                  >
                    {s.custom ? "CUSTOM" : `P${s.phase.toString().padStart(2, "0")}`}
                  </span>
                  <span className="text-base flex-shrink-0 grayscale opacity-70 group-hover:grayscale-0 group-hover:opacity-100 transition-all">
                    {s.icon}
                  </span>
                  <div className="text-left min-w-0 flex-1">
                    <div className={
                      "font-display text-[14px] italic font-light leading-tight " +
                      (active ? "text-base-100" : "text-base-200")
                    }>
                      @{s.name}
                    </div>
                    <div className="label-mono text-base-500 mt-0.5 truncate">
                      {s.desc}
                    </div>
                  </div>
                  {active && (
                    <span className="label-mono text-blue-500/80 flex-shrink-0">↵</span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
