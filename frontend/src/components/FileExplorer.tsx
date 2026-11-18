"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { ProjectFileEntry } from "../lib/types";

interface Props {
  projectId: string;
  threadId: string;
  /** Selected file path (relative to project root) so the current row can be highlighted. */
  selectedPath: string | null;
  /** Fired with the full path relative to project root when a file is clicked. */
  onFileClick: (path: string) => void;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileExplorer({
  projectId,
  threadId,
  selectedPath,
  onFileClick,
}: Props) {
  const [currentPath, setCurrentPath] = useState<string>("");
  const [entries, setEntries] = useState<ProjectFileEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (path: string) => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.listProjectFiles(projectId, threadId, path);
        setEntries(data.entries);
        setCurrentPath(data.path);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setEntries([]);
      } finally {
        setLoading(false);
      }
    },
    [projectId, threadId]
  );

  useEffect(() => {
    load("");
  }, [load]);

  const handleEntryClick = (entry: ProjectFileEntry) => {
    const joined = currentPath ? `${currentPath}/${entry.name}` : entry.name;
    if (entry.type === "dir") {
      load(joined);
    } else {
      onFileClick(joined);
    }
  };

  // Breadcrumb crumbs — empty path renders just the root. Clicking a crumb
  // jumps to that prefix; clicking root navigates to the project root.
  const crumbs = currentPath ? currentPath.split("/") : [];

  const navigateTo = (idx: number) => {
    // idx = -1 → root; otherwise navigate to crumbs[0..=idx].join("/")
    if (idx < 0) {
      load("");
    } else {
      load(crumbs.slice(0, idx + 1).join("/"));
    }
  };

  return (
    <div>
      {/* Breadcrumb path bar — root link + each segment, separated by `/`. */}
      <div className="flex items-center gap-1 mb-2 flex-wrap font-mono text-[11px]">
        <button
          onClick={() => navigateTo(-1)}
          className={
            "px-1.5 py-0.5 transition-colors " +
            (currentPath
              ? "text-base-400 hover:text-blue-300"
              : "text-blue-300")
          }
          title="Project root"
        >
          /
        </button>
        {crumbs.map((seg, i) => (
          <span key={i} className="flex items-center gap-1">
            <span className="text-base-700">/</span>
            <button
              onClick={() => navigateTo(i)}
              className={
                "px-1.5 py-0.5 transition-colors " +
                (i === crumbs.length - 1
                  ? "text-blue-300"
                  : "text-base-400 hover:text-blue-300")
              }
            >
              {seg}
            </button>
          </span>
        ))}
        <button
          onClick={() => load(currentPath)}
          className="ml-auto text-base-500 hover:text-blue-300 p-1"
          title="Refresh"
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
        </button>
      </div>

      {error && (
        <div className="px-2 py-1.5 mb-2 border border-danger/40 bg-danger/5">
          <p className="font-mono text-[11px] text-danger-400 break-words">
            {error}
          </p>
        </div>
      )}

      {loading && entries.length === 0 ? (
        <div className="px-3 py-3 text-center">
          <span className="label-mono text-base-600">LOADING…</span>
        </div>
      ) : entries.length === 0 && !error ? (
        <p className="px-3 py-2 text-[12px] text-base-500 italic font-display leading-relaxed">
          Empty directory.
        </p>
      ) : (
        <ul className="space-y-0.5">
          {entries.map((entry) => {
            const fullPath = currentPath
              ? `${currentPath}/${entry.name}`
              : entry.name;
            const isSelected =
              entry.type === "file" && selectedPath === fullPath;
            return (
              <li key={entry.name} className="relative">
                <button
                  onClick={() => handleEntryClick(entry)}
                  className={
                    "w-full flex items-center gap-2 pl-3 pr-2 py-1.5 text-left border-l transition-all " +
                    (isSelected
                      ? "border-blue-500 bg-blue-500/[0.08] text-base-100"
                      : "border-transparent hover:border-base-500 hover:bg-base-800/40 text-base-300 hover:text-base-100")
                  }
                  title={entry.type === "dir" ? "Open directory" : "Open file"}
                >
                  {/* Icon — folder glyph for dirs, dot for files. */}
                  {entry.type === "dir" ? (
                    <svg
                      width="11"
                      height="11"
                      viewBox="0 0 14 14"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.25"
                      className="text-blue-500/80 flex-shrink-0"
                    >
                      <path d="M1 3 H5 L6 4 H13 V12 H1 Z" />
                    </svg>
                  ) : (
                    <span
                      className={
                        "w-1.5 h-1.5 flex-shrink-0 " +
                        (isSelected ? "bg-blue-500 rotate-45" : "bg-base-500")
                      }
                    />
                  )}
                  <span className="font-mono text-[12px] truncate flex-1">
                    {entry.name}
                    {entry.type === "dir" && (
                      <span className="text-base-700">/</span>
                    )}
                  </span>
                  {entry.type === "file" && (
                    <span className="label-mono text-base-600 tabular-nums flex-shrink-0">
                      {formatSize(entry.size)}
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
