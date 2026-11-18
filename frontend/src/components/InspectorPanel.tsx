"use client";

import FileExplorer from "./FileExplorer";
import {
  PHASE_LABELS,
  PHASE_ORDER,
  SUBAGENTS,
  type ArtifactInfo,
  type WorkspacePhase,
} from "../lib/agents";
import type { TracingStatus } from "../lib/types";

interface Props {
  artifacts: ArtifactInfo[];
  onRefreshArtifacts: () => void;
  onArtifactClick: (name: string) => void;
  selectedArtifact: string | null;
  tracing: TracingStatus | null;
  open: boolean;
  onClose: () => void;
  onAgentClick: (name: string) => void;
  /** Project + thread the file explorer should browse. */
  projectId: string;
  threadId: string | null;
}

// Section header shared by every block in the panel. Mono label, hairline
// rule extending to the right edge — reads like a section divider on a
// specification document.
function SectionHeader({
  label,
  count,
  action,
}: {
  label: string;
  count?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="label-mono text-blue-400/80">{label}</span>
      {count && <span className="label-mono text-base-600 tabular-nums">{count}</span>}
      <div className="flex-1 h-px bg-base-700" />
      {action}
    </div>
  );
}

export default function InspectorPanel({
  artifacts,
  onRefreshArtifacts,
  onArtifactClick,
  selectedArtifact,
  tracing,
  open,
  onClose,
  onAgentClick,
  projectId,
  threadId,
}: Props) {
  if (!open) return null;

  const readyCount = artifacts.filter((a) => a.status === "ready").length;

  // Wiki-style phase grouping — one group per workspace phase folder, rendered
  // in dependency order (sources → requirements → design → planning →
  // diagrams). Each artifact carries its `phase` from the backend; we simply
  // bucket and render groups that have at least one expected artifact.
  const categories: { label: string; items: typeof artifacts }[] = (() => {
    const byPhase: Record<WorkspacePhase, typeof artifacts> = {
      sources: [],
      requirements: [],
      design: [],
      planning: [],
      diagrams: [],
    };
    for (const a of artifacts) {
      // Defensive: an artifact missing a `phase` (legacy chat / stale cache)
      // is bucketed by path prefix instead.
      const phase: WorkspacePhase =
        (a.phase as WorkspacePhase) ?? (a.name.split("/", 1)[0] as WorkspacePhase);
      if (phase in byPhase) byPhase[phase].push(a);
    }
    return PHASE_ORDER.filter((p) => byPhase[p].length > 0).map((p) => ({
      label: PHASE_LABELS[p],
      items: byPhase[p],
    }));
  })();

  // The auto-regenerated index.md sits at the workspace root — not in any
  // phase folder, so it's not in the artifacts list. We surface it as a
  // dedicated row above the phase groups so users always have one entry
  // point into the workspace.
  const indexReady = artifacts.some((a) => a.status === "ready");

  return (
    <aside className="w-[320px] min-w-[320px] lg:w-full lg:min-w-0 lg:h-full bg-base-900 border-l border-base-700 flex flex-col overflow-y-auto flex-shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between px-5 h-14 border-b border-base-700 flex-shrink-0 bg-base-950/80">
        <div className="flex flex-col leading-none">
          <span className="label-mono text-base-500 mb-0.5">INSPECTOR</span>
          <h2 className="text-[14px] text-base-100 font-medium">
            Inspector
          </h2>
        </div>
        <button
          onClick={onClose}
          className="text-base-400 hover:text-blue-300 transition-colors p-1"
          aria-label="Close inspector"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* Agent Pipeline — numbered drafting list. Phase number on the
          left, agent name in serif italic, hover-amber. */}
      <div className="px-5 py-5 border-b border-base-700">
        <SectionHeader label="PIPELINE" count={SUBAGENTS.length.toString().padStart(2, "0")} />
        <ol className="space-y-0.5">
          {SUBAGENTS.map((agent) => {
            const statusIndicator = (
              <span className="ml-auto label-mono text-base-700 group-hover:text-blue-400/80 transition-colors flex-shrink-0">
                @
              </span>
            );

            return (
              <li key={agent.name}>
                <button
                  onClick={() => onAgentClick(agent.name)}
                  className="group w-full flex items-center gap-3 pl-3 pr-2 py-2 text-left border-l border-transparent hover:border-blue-400/60 hover:bg-blue-400/[0.04] transition-all"
                  title={agent.desc}
                >
                  <span className="label-mono text-base-600 tabular-nums w-7 flex-shrink-0">
                    P{agent.phase.toString().padStart(2, "0")}
                  </span>
                  <span className="text-base flex-shrink-0 grayscale opacity-70 group-hover:grayscale-0 group-hover:opacity-100 transition-all">
                    {agent.icon}
                  </span>
                  <span className="font-display text-[14px] text-base-300 italic group-hover:text-base-100 truncate transition-colors">
                    {agent.name}
                  </span>
                  {statusIndicator}
                </button>
              </li>
            );
          })}
        </ol>
      </div>

      {/* Artifacts — grouped by type */}
      <div className="px-5 py-5 border-b border-base-700">
        <SectionHeader
          label="ARTIFACTS"
          count={
            artifacts.length > 0
              ? `${readyCount.toString().padStart(2, "0")}/${artifacts.length.toString().padStart(2, "0")}`
              : undefined
          }
          action={
            <button
              onClick={onRefreshArtifacts}
              className="text-base-500 hover:text-blue-300 transition-colors p-1"
              title="Refresh artifacts"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="23 4 23 10 17 10" />
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
              </svg>
            </button>
          }
        />
        {artifacts.length === 0 ? (
          <p className="text-[13px] text-base-500 pl-3 leading-relaxed">
            No artifacts yet. Send a message to begin.
          </p>
        ) : (
          <div className="space-y-3">
            {/* index.md — workspace entry point. Auto-regenerated by the
                backend whenever any expected artifact's mtime changes.
                Always visible (clickable once any artifact has been
                produced — that's when the file is first written). */}
            <div>
              <div className="flex items-center gap-2 mb-1.5 pl-1">
                <span className="label-mono text-blue-400/80 text-[10px] tracking-wider">
                  INDEX
                </span>
                <div className="flex-1 h-px bg-base-700/50" />
              </div>
              <ul className="space-y-0.5">
                <li className="relative">
                  <button
                    disabled={!indexReady}
                    onClick={() => indexReady && onArtifactClick("index.md")}
                    className={
                      "w-full flex items-center gap-3 pl-3 pr-2 py-1.5 text-left border-l transition-all " +
                      (indexReady
                        ? selectedArtifact === "index.md"
                          ? "border-blue-400 bg-blue-400/[0.08] text-base-100"
                          : "border-transparent hover:border-base-500 hover:bg-base-800/40 text-base-300 hover:text-base-100"
                        : "border-transparent opacity-50 cursor-not-allowed text-base-600")
                    }
                    title="Auto-regenerated workspace index"
                  >
                    {indexReady ? (
                      <span
                        className={
                          "w-2 h-2 flex-shrink-0 " +
                          (selectedArtifact === "index.md"
                            ? "bg-blue-400 rotate-45"
                            : "bg-blue-400/80")
                        }
                      />
                    ) : (
                      <span className="w-2 h-2 border border-base-600 rotate-45 flex-shrink-0" />
                    )}
                    <span className="font-mono text-[12px] truncate">index.md</span>
                  </button>
                </li>
              </ul>
            </div>

            {categories.map((cat) => {
              const catReady = cat.items.filter((a) => a.status === "ready").length;
              return (
                <div key={cat.label}>
                  {/* Category label — mono, muted, with count */}
                  <div className="flex items-center gap-2 mb-1.5 pl-1">
                    <span className="label-mono text-base-500 text-[10px] tracking-wider">
                      {cat.label}
                    </span>
                    <span className="label-mono text-base-600 tabular-nums">
                      {catReady.toString().padStart(2, "0")}/{cat.items.length.toString().padStart(2, "0")}
                    </span>
                    <div className="flex-1 h-px bg-base-700/50" />
                  </div>
                  <ul className="space-y-0.5">
                    {cat.items.map((a) => {
                      const isReady = a.status === "ready";
                      const isSelected = selectedArtifact === a.name;
                      // Show filename only (strip directory prefix)
                      const filename = a.name.includes("/") ? a.name.split("/").pop()! : a.name;
                      return (
                        <li key={a.name} className="relative">
                          <button
                            disabled={!isReady}
                            onClick={() => isReady && onArtifactClick(a.name)}
                            className={
                              "w-full flex items-center gap-3 pl-3 pr-2 py-1.5 text-left border-l transition-all " +
                              (isReady
                                ? isSelected
                                  ? "border-blue-400 bg-blue-400/[0.08] text-base-100"
                                  : "border-transparent hover:border-base-500 hover:bg-base-800/40 text-base-300 hover:text-base-100"
                                : "border-transparent opacity-50 cursor-not-allowed text-base-600")
                            }
                          >
                            {isReady ? (
                              <span className={"w-2 h-2 flex-shrink-0 " + (isSelected ? "bg-blue-400 rotate-45" : "bg-success")} />
                            ) : (
                              <span className="w-2 h-2 border border-base-600 rotate-45 flex-shrink-0" />
                            )}
                            <span className="font-mono text-[12px] truncate">{filename}</span>
                          </button>
                          {isSelected && (
                            <div className="absolute -left-px top-1/2 -translate-y-1/2 w-1.5 h-4 bg-blue-400" />
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Workspace file explorer — browse the project sandbox tree. Clicking
          a file routes through the same selectedArtifact pipe as PIPELINE
          clicks, so it opens in the ArtifactCanvas on the right. */}
      {threadId && (
        <div className="px-5 py-5 border-b border-base-700">
          <SectionHeader label="FILES" />
          <FileExplorer
            projectId={projectId}
            threadId={threadId}
            selectedPath={selectedArtifact}
            onFileClick={onArtifactClick}
          />
        </div>
      )}

      {/* Tracing — instrument readout */}
      <div className="px-5 py-5 border-b border-base-700">
        <SectionHeader label="TRACING" />
        {tracing ? (
          <div
            className={
              "flex items-center gap-3 px-3 py-2 border " +
              (tracing.enabled
                ? "border-success/40 bg-success/[0.06]"
                : "border-base-700 bg-base-950/40")
            }
            title={
              tracing.enabled
                ? "Project: " + tracing.project + "\nEndpoint: " + tracing.endpoint
                : "Set LANGSMITH_API_KEY in .env"
            }
          >
            <div className={"w-2 h-2 rounded-full " + (tracing.enabled ? "bg-success" : "bg-danger")} />
            <div className="flex flex-col leading-tight min-w-0">
              <span className={"label-mono " + (tracing.enabled ? "text-success" : "text-base-500")}>
                {tracing.enabled ? "LANGSMITH" : "DISABLED"}
              </span>
              {tracing.enabled && (
                <span className="font-mono text-[11px] text-base-400 truncate mt-0.5">
                  {tracing.project}
                </span>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 border border-base-600 border-t-transparent rounded-full animate-spin" />
            <span className="label-mono text-base-500">CHECKING…</span>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="px-5 py-5 mt-auto">
        <SectionHeader label="LEGEND" />
        <dl className="space-y-2 text-[12px] text-base-400">
          <div className="flex items-baseline gap-3">
            <dt className="font-mono text-blue-400/90 w-10 flex-shrink-0 tabular-nums">@NAME</dt>
            <dd>summon a specialist agent</dd>
          </div>
          <div className="flex items-baseline gap-3">
            <dt className="flex w-10 flex-shrink-0 items-center">
              <span className="w-2 h-2 bg-success rounded-sm" />
            </dt>
            <dd>ready — click to preview</dd>
          </div>
          <div className="flex items-baseline gap-3">
            <dt className="flex w-10 flex-shrink-0 items-center">
              <span className="w-2 h-2 border border-base-500" />
            </dt>
            <dd>pending — agent still working</dd>
          </div>
        </dl>
      </div>
    </aside>
  );
}
