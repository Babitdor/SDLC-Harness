"use client";

import { SUBAGENTS, type ArtifactInfo } from "../lib/agents";
import type { TracingStatus } from "../lib/types";

interface Props {
  projectId: string;
  onProjectIdChange: (id: string) => void;
  onCreateProject: () => void;
  artifacts: ArtifactInfo[];
  onRefreshArtifacts: () => void;
  onArtifactClick: (name: string) => void;
  selectedArtifact: string | null;
  tracing: TracingStatus | null;
  open: boolean;
  onClose: () => void;
  onAgentClick: (name: string) => void;
}

export default function AgentSidebar({
  projectId,
  onProjectIdChange,
  onCreateProject,
  artifacts,
  onRefreshArtifacts,
  onArtifactClick,
  selectedArtifact,
  tracing,
  open,
  onClose,
  onAgentClick,
}: Props) {
  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div className="fixed inset-0 bg-base-950/70 backdrop-blur-sm z-40 lg:hidden" onClick={onClose} />
      )}

      <aside
        className={
          "fixed inset-y-0 left-0 z-50 w-[300px] bg-base-900 border-r border-base-700/60 " +
          "flex flex-col overflow-y-auto transition-transform duration-200 " +
          "lg:static lg:translate-x-0 " +
          (open ? "translate-x-0" : "-translate-x-full")
        }
      >
        {/* Header */}
        <div className="flex items-center gap-2.5 px-4 h-12 border-b border-base-700/60 flex-shrink-0">
          <div className="w-7 h-7 rounded-md bg-violet-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">M</span>
          </div>
          <h1 className="text-sm font-display font-semibold text-base-100 tracking-tight">SDLC Harness</h1>
          <div className="flex-1" />
          <button onClick={onClose} className="lg:hidden text-base-500 hover:text-base-200 transition-colors p-1 rounded hover:bg-base-800">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        {/* Project ID */}
        <div className="px-4 py-3 border-b border-base-700/60">
          <h3 className="text-[10px] font-mono font-semibold uppercase tracking-[0.2em] text-base-500 mb-2">Project</h3>
          <div className="flex gap-2">
            <input
              type="text"
              value={projectId}
              onChange={(e) => onProjectIdChange(e.target.value)}
              placeholder="Project ID"
              className="flex-1 min-w-0 px-2.5 py-1.5 rounded-md bg-base-800 border border-base-700/60 text-base-200 text-xs font-mono placeholder-base-600 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-colors"
            />
            <button
              onClick={onCreateProject}
              className="px-2.5 py-1.5 rounded-md bg-violet-600 hover:bg-violet-500 text-white text-xs font-mono font-medium transition-colors flex-shrink-0"
              title="Initialize project workspace"
            >
              +init
            </button>
          </div>
        </div>

        {/* Agent Pipeline */}
        <div className="px-4 py-3 border-b border-base-700/60">
          <h3 className="text-[10px] font-mono font-semibold uppercase tracking-[0.2em] text-base-500 mb-2">Agent Pipeline</h3>
          <div className="space-y-1">
            {SUBAGENTS.map((agent, i) => (
              <button
                key={agent.name}
                onClick={() => onAgentClick(agent.name)}
                className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-left hover:bg-base-800 transition-colors group"
                title={agent.desc}
              >
                <span className="text-sm flex-shrink-0">{agent.icon}</span>
                <span className="text-[11px] font-mono text-base-300 group-hover:text-base-100 truncate">
                  {agent.name}
                </span>
                <span
                  data-phase={agent.phase}
                  className="phase-code ml-auto flex-shrink-0"
                >
                  P{agent.phase}
                </span>
                {i < SUBAGENTS.length - 1 && (
                  <span className="absolute hidden">{String.fromCharCode(8594)}</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Artifacts */}
        <div className="px-4 py-3 border-b border-base-700/60">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-[10px] font-mono font-semibold uppercase tracking-[0.2em] text-base-500">Artifacts</h3>
            <button
              onClick={onRefreshArtifacts}
              className="text-base-500 hover:text-violet-400 transition-colors p-0.5 rounded hover:bg-base-800"
              title="Refresh artifacts"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
            </button>
          </div>
          {artifacts.length === 0 ? (
            <p className="text-[11px] text-base-600 font-mono">No artifacts yet {String.fromCharCode(8594)} run +init</p>
          ) : (
            <div className="space-y-0.5">
              {artifacts.map((a) => {
                const isReady = a.status === "ready";
                const isSelected = selectedArtifact === a.name;
                return (
                  <button
                    key={a.name}
                    disabled={!isReady}
                    onClick={() => isReady && onArtifactClick(a.name)}
                    className={
                      "w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-left transition-colors " +
                      (isReady
                        ? isSelected
                          ? "bg-violet-600/20 border border-violet-500/30 text-violet-200"
                          : "hover:bg-base-800 text-base-300"
                        : "opacity-50 cursor-not-allowed text-base-500")
                    }
                  >
                    {isReady ? (
                      <svg className="w-3.5 h-3.5 text-violet-400 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                    ) : (
                      <span className="w-3.5 h-3.5 flex-shrink-0 flex items-center justify-center">
                        <span className="w-1.5 h-1.5 rounded-full bg-base-600" />
                      </span>
                    )}
                    <span className="text-[11px] font-mono truncate">{a.name}</span>
                    {isSelected && <span className="ml-auto text-[10px] font-mono text-violet-400 flex-shrink-0">{String.fromCharCode(183)} active</span>}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Tracing */}
        <div className="px-4 py-3 border-b border-base-700/60">
          <h3 className="text-[10px] font-mono font-semibold uppercase tracking-[0.2em] text-base-500 mb-2">Tracing</h3>
          {tracing ? (
            <div
              className={
                "inline-flex items-center gap-2 px-2.5 py-1.5 rounded-md text-[11px] font-mono " +
                (tracing.enabled
                  ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                  : "bg-base-800 border border-base-700/50 text-base-500")
              }
              title={
                tracing.enabled
                  ? "Project: " + tracing.project + "\nEndpoint: " + tracing.endpoint
                  : "Set LANGSMITH_API_KEY in .env"
              }
            >
              <div className={"w-1.5 h-1.5 rounded-full " + (tracing.enabled ? "bg-emerald-400" : "bg-red-400")} />
              {tracing.enabled ? "LangSmith " + String.fromCharCode(183) + " " + tracing.project : "Tracing off"}
            </div>
          ) : (
            <div className="text-[11px] text-base-600 font-mono">Checking...</div>
          )}
        </div>

        {/* How to use */}
        <div className="px-4 py-3 mt-auto">
          <h3 className="text-[10px] font-mono font-semibold uppercase tracking-[0.2em] text-base-500 mb-2">How to use</h3>
          <ul className="text-[10px] text-base-600 font-mono space-y-1.5">
            <li>
              <span className="text-violet-500/60">@</span>{" "}
              <code className="text-violet-400/80 bg-base-800 px-1 rounded text-[10px]">AgentName</code>{" "}
              invoke subagent
            </li>
            <li>
              <span className="text-violet-500/60">+</span>{" "}
              <code className="text-violet-400/80 bg-base-800 px-1 rounded text-[10px]">init</code>{" "}
              create workspace
            </li>
            <li>
              {String.fromCharCode(128065)} Click ready artifacts to preview
            </li>
          </ul>
        </div>
      </aside>
    </>
  );
}