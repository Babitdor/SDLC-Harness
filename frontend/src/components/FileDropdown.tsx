"use client";

import { useEffect, useRef } from "react";
import type { ArtifactInfo } from "../lib/agents";

interface Props {
  /** Already-filtered list of workspace files to display. ChatInput owns
   * the filtering so the matching rules stay in one place. */
  items: ArtifactInfo[];
  activeIndex: number;
  /** Called with the file's phase-qualified path, e.g. "logical/BDD.md". */
  onSelect: (path: string) => void;
  visible: boolean;
}

function basename(path: string): string {
  const i = path.lastIndexOf("/");
  return i === -1 ? path : path.slice(i + 1);
}

export default function FileDropdown({ items, activeIndex, onSelect, visible }: Props) {
  const listRef = useRef<HTMLUListElement>(null);
  const activeItemRef = useRef<HTMLLIElement>(null);

  useEffect(() => {
    if (!visible) return;
    activeItemRef.current?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, visible]);

  if (!visible) return null;
  if (items.length === 0) return null;

  // Mirror MentionDropdown's split-node structure: a plain positioning
  // wrapper around the `tick-corners` panel (which sets position:relative
  // and would otherwise fight the absolute anchor).
  return (
    <div
      className="absolute bottom-full left-6 right-6 mb-3 z-50 pointer-events-none"
      style={{ position: "absolute" }}
    >
      <div className="pointer-events-auto bg-base-900 border border-base-600 min-w-[300px] max-w-md tick-corners max-h-[60vh] flex flex-col shadow-lg shadow-base-950/50">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-base-700 flex-shrink-0">
          <span className="label-mono text-blue-500/80">REFERENCE FILE</span>
          <div className="flex-1 h-px bg-base-700" />
          <span className="label-mono text-base-600 tabular-nums">
            {items.length.toString().padStart(2, "0")}
          </span>
        </div>

        <ul ref={listRef} className="overflow-y-auto">
          {items.map((f, i) => {
            const active = i === activeIndex;
            return (
              <li key={f.name} ref={active ? activeItemRef : null}>
                <button
                  className={
                    "group w-full flex items-center gap-3 px-3 py-2 text-left border-l-2 transition-all " +
                    (active
                      ? "border-blue-500 bg-blue-500/[0.08]"
                      : "border-transparent hover:border-base-500 hover:bg-base-800/40")
                  }
                  onMouseDown={(e) => {
                    // Prevent textarea blur before the click handler fires.
                    e.preventDefault();
                    onSelect(f.name);
                  }}
                >
                  <span
                    className={
                      "label-mono px-1.5 py-1 border uppercase flex-shrink-0 " +
                      (active
                        ? "border-blue-500/60 text-blue-300"
                        : "border-base-700 text-base-500 group-hover:text-base-300")
                    }
                  >
                    {f.phase}
                  </span>
                  <div className="text-left min-w-0 flex-1">
                    <div
                      className={
                        "font-mono text-[13px] leading-tight truncate " +
                        (active ? "text-base-100" : "text-base-200")
                      }
                    >
                      {basename(f.name)}
                    </div>
                    <div className="label-mono text-base-500 mt-0.5 truncate">
                      {f.name}
                    </div>
                  </div>
                  {f.status === "pending" && (
                    <span className="label-mono text-amber-500/70 flex-shrink-0">…</span>
                  )}
                  {active && f.status !== "pending" && (
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
