"use client";

import { useEffect, useRef } from "react";

export interface SlashCommandInfo {
  name: string;
  desc: string;
}

interface Props {
  items: SlashCommandInfo[];
  activeIndex: number;
  onSelect: (name: string) => void;
  visible: boolean;
}

export default function SlashDropdown({ items, activeIndex, onSelect, visible }: Props) {
  const listRef = useRef<HTMLUListElement>(null);
  const activeItemRef = useRef<HTMLLIElement>(null);

  useEffect(() => {
    if (!visible) return;
    activeItemRef.current?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, visible]);

  if (!visible) return null;
  if (items.length === 0) return null;

  return (
    <div
      className="absolute bottom-full left-6 right-6 mb-3 z-50 pointer-events-none"
      style={{ position: "absolute" }}
    >
      <div className="pointer-events-auto bg-base-900 border border-base-600 min-w-[300px] max-w-md tick-corners max-h-[60vh] flex flex-col shadow-lg shadow-base-950/50">
        {/* Header row — binder label */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-base-700 flex-shrink-0">
          <span className="label-mono text-blue-500/80">COMMANDS</span>
          <div className="flex-1 h-px bg-base-700" />
          <span className="label-mono text-base-600 tabular-nums">
            {items.length.toString().padStart(2, "0")}
          </span>
        </div>

        <ul ref={listRef} className="overflow-y-auto">
          {items.map((cmd, i) => {
            const active = i === activeIndex;
            return (
              <li key={cmd.name} ref={active ? activeItemRef : null}>
                <button
                  className={
                    "group w-full flex items-center gap-3 px-3 py-2 text-left border-l-2 transition-all " +
                    (active
                      ? "border-blue-500 bg-blue-500/[0.08]"
                      : "border-transparent hover:border-base-500 hover:bg-base-800/40")
                  }
                  onMouseDown={(e) => {
                    // Prevent textarea blur
                    e.preventDefault();
                    onSelect(cmd.name);
                  }}
                >
                  {/* Command badge */}
                  <span
                    className={
                      "label-mono px-1.5 py-1 border flex-shrink-0 " +
                      (active
                        ? "border-blue-500/60 text-blue-300"
                        : "border-base-700 text-base-500 group-hover:text-base-300")
                    }
                  >
                    CMD
                  </span>
                  <span className="text-base flex-shrink-0 opacity-70 group-hover:opacity-100 transition-all text-blue-400">
                    ⚡
                  </span>
                  <div className="text-left min-w-0 flex-1">
                    <div className={
                      "font-display text-[14px] font-medium leading-tight " +
                      (active ? "text-base-100" : "text-base-200")
                    }>
                      /{cmd.name}
                    </div>
                    <div className="label-mono text-base-500 mt-0.5 truncate text-[11px]">
                      {cmd.desc}
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
