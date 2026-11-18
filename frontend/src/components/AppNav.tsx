"use client";

import { useAuthSession } from "./AuthGate";
import type { SidebarTab } from "./ChatSidebar";
import { ThemeToggle } from "./ThemeToggle";

interface Props {
  /** Active sidebar section. The tab buttons live here now, not in the sidebar. */
  tab: SidebarTab;
  onTabChange: (tab: SidebarTab) => void;
  inspectorOpen: boolean;
  onToggleInspector: () => void;
  health: { loading: boolean; connected: boolean; containerRunning: boolean };
  /** Mobile: reveal the sidebar drawer. */
  onToggleSidebar: () => void;
}

const TABS: { id: SidebarTab; label: string; path: string }[] = [
  { id: "threads", label: "THREADS", path: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" },
  { id: "agents", label: "AGENTS", path: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 7a4 4 0 1 0 0 .01" },
  { id: "skills", label: "SKILLS", path: "M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" },
  { id: "mcp", label: "MCP", path: "M3 4h18v6H3zM3 14h18v6H3z" },
  { id: "settings", label: "SETTINGS", path: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-2.82 1.18V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9" },
];

/** "requirements/REQUIREMENTS.md" -> "REQUIREMENTS.md" */
const baseName = (name: string) => name.split("/").pop() ?? name;

export default function AppNav({
  tab,
  onTabChange,
  inspectorOpen,
  onToggleInspector,
  health,
  onToggleSidebar,
}: Props) {
  // Null when rendered outside <AuthGate> (e.g. the component's own test), so
  // the cluster simply does not appear.
  const session = useAuthSession();

  return (
    <nav className="flex items-center gap-3 h-12 px-3 border-b border-base-700 bg-base-900/80 flex-shrink-0 z-30">
      <button
        onClick={onToggleSidebar}
        className="lg:hidden text-base-400 hover:text-blue-300 transition-colors"
        aria-label="Toggle sidebar"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      <div className="flex items-baseline gap-2 flex-shrink-0 mr-1">
        <span className="label-mono text-blue-400/80 hidden sm:inline">SDLC / V0.2</span>
        <span className="dossier-title text-[15px] text-base-100">Harness</span>
      </div>

      {/* Section tabs. Scrolls horizontally on narrow screens: with five icons
          plus the action cluster, a fixed row clips the tabs off-screen at
          mobile widths, which would hide the whole navigation. */}
      <div className="flex items-stretch h-full border-l border-base-700 min-w-0 flex-1 overflow-x-auto">
        {TABS.map((item) => {
          const isActive = tab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              title={item.label}
              aria-current={isActive ? "page" : undefined}
              className={
                "flex items-center gap-1.5 px-2.5 label-mono transition-colors border-b-2 " +
                (isActive
                  ? "text-blue-300 border-blue-400 bg-blue-400/5"
                  : "text-base-500 border-transparent hover:text-base-200 hover:bg-base-800/50")
              }
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0">
                <path d={item.path} />
              </svg>
              <span className="hidden xl:inline">{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">

        <button
          onClick={onToggleInspector}
          className={
            "p-1.5 border transition-colors " +
            (inspectorOpen
              ? "border-blue-400/60 bg-blue-400/10 text-blue-300"
              : "border-base-600 text-base-400 hover:text-base-100 hover:border-base-500")
          }
          title="Toggle Inspector"
          aria-label="Toggle Inspector"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="1" />
            <line x1="9" y1="3" x2="9" y2="21" />
          </svg>
        </button>

        {session && (
          <div className="hidden md:flex items-center gap-2 border-l border-base-700 pl-2">
            <span
              className="label-mono text-base-500 max-w-[18ch] truncate"
              title={session.user.email}
            >
              {session.user.email}
            </span>
            <button
              type="button"
              onClick={() => void session.signOut()}
              className="label-mono text-base-400 hover:text-blue-300 transition-colors cursor-pointer"
              title="Sign out"
            >
              SIGN OUT
            </button>
          </div>
        )}

        <ThemeToggle />

        <span
          className={
            "gate-badge hidden md:inline-flex " +
            (health.connected && health.containerRunning
              ? "border-success/40 text-success"
              : "border-danger/40 text-danger-400")
          }
        >
          <span className="label-mono">
            {health.loading
              ? "LINKING…"
              : health.connected && health.containerRunning
                ? "GATE OPEN"
                : "GATE SHUT"}
          </span>
        </span>
      </div>
    </nav>
  );
}
