"use client";

import { useState, useRef } from "react";
import AgentsPanel from "./AgentsPanel";
import McpPanel from "./McpPanel";
import SettingsPanel from "./SettingsPanel";
import SkillsPanel from "./SkillsPanel";
import type { Conversation } from "../lib/types";
import { api } from "../lib/api";

/** Sections of the sidebar body. Owned by the page (AppNav renders the tabs). */
export type SidebarTab = "threads" | "agents" | "settings" | "skills" | "mcp";

const SECTION_LABELS: Record<SidebarTab, string> = {
  threads: "THREADS",
  agents: "AGENTS",
  settings: "SETTINGS",
  skills: "SKILLS",
  mcp: "MCP",
};

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  /** Thread IDs whose backend agent is still running. Renders a small
   *  WORKING chip on those rows so the user knows work is in progress
   *  even on threads they've navigated away from. Optional so callers
   *  that don't track this state can omit it. */
  inFlight?: Set<string>;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, newTitle: string) => void;
  /** Mobile slide-in state */
  open: boolean;
  onClose: () => void;
  /** Desktop rail mode — narrow icon-only sidebar */
  collapsed: boolean;
  onToggleCollapsed: () => void;
  selectedSkill: string | null;
  onSelectSkill: (name: string | null) => void;
  /** Active section — the tab buttons live in the header navbar (AppNav). */
  tab: SidebarTab;
}

export default function ChatSidebar({
  conversations,
  activeId,
  inFlight,
  onSelect,
  onNew,
  onDelete,
  onRename,
  open,
  onClose,
  collapsed,
  onToggleCollapsed,
  selectedSkill,
  onSelectSkill,
  tab,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Inline rename — one row at a time. `renamingId` is the conversation
  // currently in edit mode; `draftTitle` is the in-flight input value.
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");

  const commitRename = (id: string) => {
    const trimmed = draftTitle.trim().slice(0, 200);
    // Empty submit silently cancels — never blank a row's title.
    if (trimmed) onRename(id, trimmed);
    setRenamingId(null);
    setDraftTitle("");
  };

  const cancelRename = () => {
    setRenamingId(null);
    setDraftTitle("");
  };

  // Export the thread as a Markdown transcript (messages, tool calls
  // with input+output, agent reasoning). The backend sets
  // Content-Disposition: attachment, so a plain <a> click saves the file.
  const exportThread = (id: string) => {
    const url = api.exportConversationUrl(id);
    const a = document.createElement("a");
    a.href = url;
    a.download = "";
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const formatDate = (ts: number) => {
    const d = new Date(ts);
    const now = new Date();
    const diffDays = Math.floor(
      (now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24)
    );
    if (diffDays === 0) return "TODAY";
    if (diffDays === 1) return "YESTERDAY";
    if (diffDays < 7) return `${diffDays}D AGO`;
    return d
      .toLocaleDateString(undefined, { month: "short", day: "numeric" })
      .toUpperCase();
  };

  const truncate = (s: string, max: number) =>
    s.length > max ? s.slice(0, max) + "…" : s;

  // Sorted-by-recent: shared between rail and expanded views so the
  // "most recent" semantic stays consistent across modes.
  const sortedConversations = [...conversations].sort(
    (a, b) => b.updatedAt - a.updatedAt
  );

  // ── Mobile overlay (only when sliding in on small screens) ──────────
  const mobileOverlay = open ? (
    <div
      className="fixed inset-0 bg-base-950/80 backdrop-blur-sm z-40 lg:hidden"
      onClick={onClose}
    />
  ) : null;

  // ── RAIL MODE (collapsed, desktop only) ──────────────────────────────
  // A 56px-wide column with: vertical wordmark, new-thread sigil, a
  // stack of recent threads as compact rotated-diamond markers (active
  // amber, others muted), and the expand toggle at the bottom. Mobile
  // falls through to the expanded variant via the slide-in overlay.
  if (collapsed) {
    return (
      <>
        {mobileOverlay}
        <aside
          className={
            "fixed inset-y-0 left-0 z-50 w-14 bg-base-900 border-r border-base-700 " +
            "flex flex-col items-center overflow-hidden transition-transform duration-200 " +
            // On desktop the rail is inside a resizable Panel resized to
            // ~5% by the collapse toggle. `lg:w-full` lets the rail content
            // align to whatever the Panel width is (rail items are
            // centered, so a slightly wider Panel just adds breathing room).
            "lg:static lg:translate-x-0 lg:w-full lg:h-full " +
            (open ? "translate-x-0" : "-translate-x-full lg:translate-x-0")
          }
        >
          {/* Top — wordmark */}
          <div className="flex flex-col items-center py-4 border-b border-base-700 w-full">
            <span className="label-mono text-base-400" style={{ writingMode: "vertical-rl", letterSpacing: "0.18em" }}>
              HARNESS
            </span>
          </div>

          {/* New thread — compact sigil button */}
          <button
            onClick={onNew}
            className="group mt-4 mb-2 w-10 h-10 flex items-center justify-center border border-base-600 hover:border-blue-400/60 hover:bg-blue-400/10 transition-all"
            title="New thread"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="text-base-300 group-hover:text-blue-300"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>

          {/* Recent threads — vertical strip of compact markers. Hover
              reveals the thread title in a native tooltip; clicking the
              marker activates that thread without expanding the rail. */}
          <div className="flex-1 w-full overflow-y-auto py-2 px-1 flex flex-col items-center gap-1.5">
            {sortedConversations.slice(0, 12).map((conv) => {
              const isActive = conv.id === activeId;
              return (
                <button
                  key={conv.id}
                  onClick={() => onSelect(conv.id)}
                  title={conv.title || "Untitled thread"}
                  className={
                    "w-10 h-8 flex items-center justify-center transition-all border-l-2 " +
                    (isActive
                      ? "border-blue-400 bg-blue-400/[0.08]"
                      : "border-transparent hover:border-base-500 hover:bg-base-800/40")
                  }
                >
                  <span
                    className={
                      "block " +
                      (isActive
                        ? "w-2 h-2 bg-blue-400 rotate-45"
                        : "w-1.5 h-1.5 border border-base-500 rotate-45")
                    }
                  />
                </button>
              );
            })}
          </div>

          {/* Footer — expand button */}
          <div className="w-full border-t border-base-700 py-3 flex flex-col items-center gap-3">
            <button
              onClick={onToggleCollapsed}
              className="w-10 h-8 flex items-center justify-center text-base-500 hover:text-blue-300 border border-base-700 hover:border-base-500 transition-colors hidden lg:flex"
              title="Expand sidebar"
              aria-label="Expand sidebar"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          </div>
        </aside>
      </>
    );
  }

  // ── EXPANDED MODE ────────────────────────────────────────────────────
  return (
    <>
      {mobileOverlay}

      <aside
        ref={containerRef}
        className={
          "fixed inset-y-0 left-0 z-50 w-[280px] bg-base-900 border-r border-base-700 " +
          "flex flex-col overflow-hidden transition-transform duration-200 " +
          // On desktop the sidebar lives inside a resizable Panel — let
          // the Panel control the width instead of hard-pinning to 280px.
          // `lg:h-full` pins the aside to the Panel height so its inner
          // scroll regions have a definite container to overflow against.
          "lg:static lg:translate-x-0 lg:w-full lg:h-full " +
          (open ? "translate-x-0" : "-translate-x-full lg:translate-x-0")
        }
      >
        {/* Header */}
        <div className="flex-shrink-0 px-5 pt-5 pb-4 border-b border-base-700 relative">
          <div className="flex items-center justify-between mb-5">
            {/* The wordmark moved to the header navbar; this row names the
                section the sidebar is currently showing instead. */}
            <span className="label-mono text-blue-400/80">{SECTION_LABELS[tab]}</span>
            <div className="flex items-center gap-1">
              {/* Desktop collapse toggle */}
              <button
                onClick={onToggleCollapsed}
                className="hidden lg:flex w-7 h-7 items-center justify-center text-base-500 hover:text-blue-300 border border-transparent hover:border-base-600 transition-colors"
                title="Collapse sidebar"
                aria-label="Collapse sidebar"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
              </button>
              {/* Mobile close */}
              <button
                onClick={onClose}
                className="lg:hidden text-base-400 hover:text-base-100 transition-colors p-1"
                aria-label="Close sidebar"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>

        </div>

        {tab === "agents" ? (
          <AgentsPanel active={tab === "agents"} />
        ) : tab === "settings" ? (
          <SettingsPanel active={tab === "settings"} />
        ) : tab === "skills" ? (
          <SkillsPanel active={tab === "skills"} onSelectSkill={onSelectSkill} selectedSkill={selectedSkill} />
        ) : tab === "mcp" ? (
          <McpPanel active={tab === "mcp"} />
        ) : (
          <>
        {/* New thread */}
        <div className="flex-shrink-0 px-5 pt-4 pb-3 border-b border-base-700">
          <button
            onClick={onNew}
            className="group w-full flex items-center justify-between px-3 py-2.5
                       border border-base-600 hover:border-blue-400/60
                       bg-base-800/40 hover:bg-base-800/80
                       transition-all duration-200 relative
                       tick-corners"
          >
            <span className="label-mono text-base-300 group-hover:text-blue-300 transition-colors">
              + NEW THREAD
            </span>
            <span className="font-mono text-[10px] text-base-500 group-hover:text-blue-400/70 transition-colors">
              ↵
            </span>
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto px-3 py-4">
          <div className="label-mono text-base-500 px-2 mb-3 flex items-center gap-2">
            <span>THREADS</span>
            <div className="flex-1 h-px bg-base-700" />
            <span className="text-base-600 tabular-nums">
              {conversations.length.toString().padStart(2, "0")}
            </span>
          </div>

          {conversations.length === 0 ? (
            <div className="px-3 py-8 text-center">
              <p className="font-display text-sm text-base-400 italic">
                No threads yet.
              </p>
              <p className="label-mono text-base-600 mt-2">
                START A NEW THREAD ABOVE
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {sortedConversations.map((conv) => {
                const isActive = conv.id === activeId;
                const isRenaming = renamingId === conv.id;
                return (
                  <div key={conv.id} className="group relative">
                    <button
                      onClick={() => {
                        // While renaming this row, the outer button is inert
                        // so a misplaced click doesn't switch conversations.
                        if (!isRenaming) onSelect(conv.id);
                      }}
                      className={
                        // pr-24 leaves room for all three action buttons
                        // (export + rename + delete) without overlapping the
                        // title text.
                        "w-full text-left pl-4 pr-24 py-2.5 transition-all duration-150 relative " +
                        (isActive
                          ? "bg-blue-400/[0.07] border-l-2 border-blue-400"
                          : "border-l-2 border-transparent hover:border-base-500 hover:bg-base-800/40")
                      }
                    >
                      {isActive && (
                        <div className="absolute -left-[5px] top-1/2 -translate-y-1/2 w-2 h-2 bg-blue-400 rotate-45" />
                      )}
                      {isRenaming ? (
                        <input
                          autoFocus
                          value={draftTitle}
                          onChange={(e) => setDraftTitle(e.target.value)}
                          onFocus={(e) => e.currentTarget.select()}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              commitRename(conv.id);
                            } else if (e.key === "Escape") {
                              e.preventDefault();
                              cancelRename();
                            }
                          }}
                          onBlur={() => commitRename(conv.id)}
                          onClick={(e) => e.stopPropagation()}
                          maxLength={200}
                          className="w-full bg-base-900 border border-blue-400/60 text-[13px] leading-tight font-medium text-base-100 px-1.5 py-0.5 -my-0.5 outline-none"
                        />
                      ) : (
                        <div
                          className={
                            "text-[13px] leading-tight truncate font-medium " +
                            (isActive
                              ? "text-base-100"
                              : "text-base-300 group-hover:text-base-100")
                          }
                        >
                          {truncate(conv.title || "Untitled thread", 26)}
                        </div>
                      )}
                      <div className="flex items-center gap-2 mt-1.5">
                        <span
                          className={
                            "label-mono " +
                            (isActive ? "text-blue-400/80" : "text-base-500")
                          }
                        >
                          {formatDate(conv.updatedAt)}
                        </span>
                        {conv.messageCount > 0 && (
                          <>
                            <span className="text-base-700">·</span>
                            <span className="font-mono text-[10px] text-base-500 tabular-nums">
                              {conv.messageCount.toString().padStart(2, "0")} MSG
                            </span>
                          </>
                        )}
                        {inFlight?.has(conv.id) && (
                          // Backend agent still running for this thread.
                          // Static "⚡ WORKING" tag plus a pulsing amber
                          // dot so the eye catches in-flight threads at a
                          // glance even when not active.
                          <>
                            <span className="text-base-700">·</span>
                            <span className="inline-flex items-center gap-1.5 label-mono text-blue-300">
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                              WORKING
                            </span>
                          </>
                        )}
                      </div>
                    </button>

                    {/* Action icons — hidden while renaming so they don't
                        compete with the input or capture the blur.
                        One flex row rather than three absolutely-positioned
                        buttons: spacing is declared once, adding a fourth
                        action needs no re-tuning, and the show/hide rule
                        lives in a single place instead of being repeated
                        (and drifting) across each button. */}
                    {!isRenaming && (
                      <div
                        className={
                          "absolute right-2 top-1/2 -translate-y-1/2 " +
                          "flex items-center gap-0.5 transition-opacity " +
                          (isActive ? "" : "opacity-0 group-hover:opacity-100")
                        }
                      >
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            exportThread(conv.id);
                          }}
                          className={
                            "p-1.5 transition-colors " +
                            (isActive
                              ? "text-base-500 hover:text-blue-300"
                              : "text-base-600 hover:text-blue-300")
                          }
                          title="Export thread (Markdown)"
                        >
                          <svg
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                            <polyline points="7 10 12 15 17 10" />
                            <line x1="12" y1="15" x2="12" y2="3" />
                          </svg>
                        </button>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setRenamingId(conv.id);
                            setDraftTitle(conv.title || "");
                          }}
                          className={
                            "p-1.5 transition-colors " +
                            (isActive
                              ? "text-base-500 hover:text-blue-300"
                              : "text-base-600 hover:text-blue-300")
                          }
                          title="Rename thread"
                        >
                          <svg
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M17 3a2.85 2.85 0 014 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                          </svg>
                        </button>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDelete(conv.id);
                          }}
                          className={
                            "p-1.5 transition-colors " +
                            (isActive
                              ? "text-base-500 hover:text-danger"
                              : "text-base-600 hover:text-danger")
                          }
                          title="Delete thread"
                        >
                          <svg
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                          </svg>
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
          </>
        )}

        {/* Footer */}
        <div className="flex-shrink-0 px-5 py-3 border-t border-base-700">
          <div className="flex items-center justify-between">
            <span className="label-mono text-base-600">REV.0.2</span>
            <span className="label-mono text-base-500">ORCHESTRATOR</span>
          </div>
        </div>
      </aside>
    </>
  );
}
