"use client";

import { useEffect, useRef, useState } from "react";
import { PHASE_ORDER, type ArtifactInfo } from "../lib/agents";

interface Props {
  artifacts: ArtifactInfo[];
  selectedArtifact: string | null;
  onSelectArtifact: (name: string | null) => void;
  inspectorOpen: boolean;
  onToggleInspector: () => void;
}

/** "requirements/REQUIREMENTS.md" -> "REQUIREMENTS.md" */
const baseName = (name: string) => name.split("/").pop() ?? name;

/**
 * Artifact viewer entry point for the chat header.
 *
 * Lists what the current dossier has produced, ready artifacts first, and
 * opens one in the artifact canvas on click. It sits next to the document
 * title because that is the thing it belongs to — the files this thread wrote —
 * not in the app-wide navbar.
 */
export default function ArtifactsMenu({
  artifacts,
  selectedArtifact,
  onSelectArtifact,
  inspectorOpen,
  onToggleInspector,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click / Escape — a dropdown that survives a click
  // elsewhere covers the transcript it is supposed to help you read.
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  const ready = artifacts.filter((a) => a.status === "ready");
  const pending = artifacts.filter((a) => a.status !== "ready");

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setMenuOpen((open) => !open)}
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        className={
          "flex items-center gap-2 px-2.5 py-1.5 border transition-colors label-mono " +
          (menuOpen || selectedArtifact
            ? "border-blue-400/60 text-blue-300 bg-blue-400/10"
            : "border-base-600 text-base-400 hover:text-base-100 hover:border-base-500")
        }
        title="Artifacts"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
          <polyline points="13 2 13 9 20 9" />
        </svg>
        <span className="hidden sm:inline">ARTIFACTS</span>
        <span className="tabular-nums text-[10px] text-base-500">
          {ready.length.toString().padStart(2, "0")}
        </span>
        <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {menuOpen && (
        <div
          role="menu"
          className="absolute right-0 mt-1 w-[300px] max-h-[70vh] overflow-y-auto border border-base-600 bg-base-900 shadow-xl z-50"
        >
          <div className="px-3 py-2 border-b border-base-700 flex items-center gap-2">
            <span className="label-mono text-base-400">SPECIFICATIONS</span>
            <span className="label-mono text-base-600 ml-auto tabular-nums">
              {ready.length}/{artifacts.length}
            </span>
          </div>

          {artifacts.length === 0 ? (
            <p className="px-3 py-6 text-center font-display text-[12px] text-base-500 italic">
              No artifacts yet — they appear as the phases write them.
            </p>
          ) : (
            [...ready, ...pending].map((artifact) => {
              // Only ready artifacts have bytes to load. Clicking a pending one
              // opens the canvas on a guaranteed 404, so it is listed but inert.
              const isReady = artifact.status === "ready";
              return (
              <button
                key={artifact.name}
                role="menuitem"
                disabled={!isReady}
                title={isReady ? artifact.name : `${artifact.name} — not written yet`}
                onClick={() => {
                  if (!isReady) return;
                  onSelectArtifact(artifact.name);
                  setMenuOpen(false);
                }}
                className={
                  "w-full flex items-center gap-2 px-3 py-1.5 text-left transition-colors " +
                  (isReady ? "hover:bg-base-800/70 cursor-pointer" : "cursor-default opacity-60") +
                  " " +
                  (selectedArtifact === artifact.name ? "bg-blue-400/10" : "")
                }
              >
                <span
                  className={
                    "w-1.5 h-1.5 flex-shrink-0 rounded-full " +
                    (artifact.status === "ready" ? "bg-blue-400" : "bg-base-600")
                  }
                />
                <span className="font-mono text-[11px] text-base-200 truncate">
                  {baseName(artifact.name)}
                </span>
                {/* The palette keys on 1–5, not the phase folder name. */}
                <span
                  data-phase={PHASE_ORDER.indexOf(artifact.phase) + 1}
                  className="phase-code ml-auto flex-shrink-0"
                >
                  {artifact.phase}
                </span>
              </button>
              );
            })
          )}

          <button
            onClick={() => {
              onToggleInspector();
              setMenuOpen(false);
            }}
            className="w-full px-3 py-2 border-t border-base-700 label-mono text-base-500 hover:text-blue-300 transition-colors text-left"
          >
            {inspectorOpen ? "CLOSE INSPECTOR" : "OPEN INSPECTOR →"}
          </button>
        </div>
      )}
    </div>
  );
}
