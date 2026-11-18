"use client";

import { memo, useMemo, useState } from "react";
import DiffPreview from "./DiffPreview";

export interface ToolCallBlockProps {
  toolName: string;
  toolArgs?: string;
  result?: string;
  isRunning?: boolean;
}

// `content-visibility: auto` lets the browser skip layout/paint for the
// off-screen portion of a long streamed result (e.g. REQUIREMENTS.md
// scrolling in line-by-line). `contain-intrinsic-size` gives a size
// hint so the scroller doesn't jump while content streams in.
const preStyle: React.CSSProperties = {
  contentVisibility: "auto",
  containIntrinsicSize: "auto 200px",
};

// Hard cap on chars rendered on first expand. Above this, the browser's
// text-shaping work on `whitespace-pre-wrap break-words` locks the main
// thread (a single read_file on a 50KB skill is enough to freeze the UI
// for seconds). The user can opt into the full payload with a second click.
const MAX_RENDER_CHARS = 8000;

function truncate(s: string): { shown: string; remaining: number } {
  if (s.length <= MAX_RENDER_CHARS) return { shown: s, remaining: 0 };
  return { shown: s.slice(0, MAX_RENDER_CHARS), remaining: s.length - MAX_RENDER_CHARS };
}

/**
 * Parse tool args from a JSON string, returning a dict or null.
 */
function parseArgs(raw: string | undefined): Record<string, unknown> | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * Extract the old_string and new_string from an edit_file tool call's args.
 */
function getEditDiff(args: Record<string, unknown>): { oldContent: string; newContent: string } | null {
  const oldString = args.old_string as string | undefined;
  const newString = args.new_string as string | undefined;
  if (oldString == null && newString == null) return null;
  return { oldContent: oldString ?? "", newContent: newString ?? "" };
}

/**
 * Extract the content from a write_file tool call's args.
 */
function getWriteContent(args: Record<string, unknown>): string | null {
  return (args.content as string) ?? null;
}

function ToolCallBlockImpl({ toolName, toolArgs, result, isRunning }: ToolCallBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const [showFullArgs, setShowFullArgs] = useState(false);
  const [showFullResult, setShowFullResult] = useState(false);
  const [showDiff, setShowDiff] = useState(false);

  const displayName = toolName.toUpperCase().replace(/_/g, " ");

  const hasError = result && (result.includes("[Command failed") || result.includes("error") || result.includes("Error"));
  const hasResult = !!result;
  const hasArgs = !!toolArgs;

  // ── Diff preview for edit_file / write_file ─────────────────────────
  const isEditFile = toolName === "edit_file";
  const isWriteFile = toolName === "write_file";
  const parsedArgs = useMemo(() => parseArgs(toolArgs), [toolArgs]);
  const editDiff = useMemo(
    () => (isEditFile && parsedArgs ? getEditDiff(parsedArgs) : null),
    [isEditFile, parsedArgs],
  );
  const writeContent = useMemo(
    () => (isWriteFile && parsedArgs ? getWriteContent(parsedArgs) : null),
    [isWriteFile, parsedArgs],
  );
  const showDiffButton = (isEditFile && editDiff) || (isWriteFile && writeContent);

  // Status icon — drafting-style: small filled square (active), open
  // diamond (idle), filled checkmark (success), x (error). All hand-drawn
  // shapes from primitives, no stock icons.
  const statusIcon = isRunning && !hasResult ? (
    <div className="w-2.5 h-2.5 border border-blue-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
  ) : hasError ? (
    <span className="text-danger-400 font-mono text-xs leading-none flex-shrink-0">×</span>
  ) : hasResult ? (
    <span className="w-2 h-2 bg-success rotate-45 flex-shrink-0" />
  ) : (
    <span className="w-2 h-2 border border-base-500 rotate-45 flex-shrink-0" />
  );

  return (
    <div className="my-3 border border-base-700 bg-base-900/50 relative">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-base-800/60 transition-colors group"
      >
        {statusIcon}
        <span className="label-mono text-base-200 flex-shrink-0">
          {displayName}
        </span>
        {hasArgs && (
          <span className="font-mono text-[11px] text-base-400 flex-1 truncate min-w-0">
            {toolArgs.length > 80 ? toolArgs.slice(0, 80) + "…" : toolArgs}
            {isRunning && !hasResult && (
              <span className="inline-block w-1 h-3 bg-blue-400 ml-1 align-middle animate-pulse" />
            )}
          </span>
        )}
        {!hasArgs && (
          <span className="flex-1" />
        )}
        {/* SHOW DIFF toggle — only for edit_file / write_file */}
        {showDiffButton && !isRunning && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowDiff((v) => !v);
            }}
            className={
              "label-mono px-2 py-0.5 border text-[10px] transition-colors mr-1 " +
              (showDiff
                ? "border-cyan-500/60 bg-cyan-500/10 text-cyan-300"
                : "border-base-600 text-base-500 hover:text-base-200 hover:border-base-500")
            }
          >
            {showDiff ? "HIDE DIFF" : "SHOW DIFF"}
          </button>
        )}
        <svg
          className={"w-3 h-3 text-base-500 transition-transform flex-shrink-0 group-hover:text-blue-300 " + (expanded ? "rotate-180" : "")}
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {/* Diff preview — shown inline when toggled */}
      {showDiff && editDiff && (
        <div className="border-t border-base-700">
          <DiffPreview
            oldContent={editDiff.oldContent}
            newContent={editDiff.newContent}
            filename={(parsedArgs?.file_path as string) ?? undefined}
          />
        </div>
      )}
      {showDiff && isWriteFile && writeContent && (
        <div className="border-t border-base-700">
          <DiffPreview
            oldContent=""
            newContent={writeContent}
            filename={(parsedArgs?.file_path as string) ?? undefined}
          />
        </div>
      )}

      {(hasArgs || hasResult) && expanded && (
        <div className="border-t border-base-700 px-4 py-3 bg-base-950/40">
          {hasArgs && (() => {
            const t = truncate(toolArgs!);
            const argsToRender = showFullArgs ? toolArgs! : t.shown;
            return (
              <div className="mb-3">
                <div className="label-mono text-base-500 mb-1.5 flex items-center gap-2">
                  <span>ARGUMENTS</span>
                  <div className="flex-1 h-px bg-base-700" />
                </div>
                <pre style={preStyle} className="font-mono text-[11px] text-base-300 whitespace-pre-wrap break-words max-h-32 overflow-y-auto leading-relaxed pl-3 border-l border-blue-400/30">{argsToRender}</pre>
                {t.remaining > 0 && !showFullArgs && (
                  <button
                    onClick={() => setShowFullArgs(true)}
                    className="label-mono text-blue-400/80 hover:text-blue-300 mt-1.5 ml-3"
                  >
                    Show full arguments (+{t.remaining.toLocaleString()} chars) ↓
                  </button>
                )}
              </div>
            );
          })()}
          {hasResult && (() => {
            const t = truncate(result!);
            const resultToRender = showFullResult ? result! : t.shown;
            return (
              <div>
                <div className="label-mono text-base-500 mb-1.5 flex items-center gap-2">
                  <span>RESULT</span>
                  <div className="flex-1 h-px bg-base-700" />
                  {hasError && <span className="label-mono text-danger-400">ERR</span>}
                </div>
                <pre style={preStyle} className={
                  "font-mono text-[11px] whitespace-pre-wrap break-words max-h-64 overflow-y-auto leading-relaxed pl-3 border-l " +
                  (hasError ? "border-danger/40 text-danger-400" : "border-cyan-500/30 text-base-300")
                }>{resultToRender}</pre>
                {t.remaining > 0 && !showFullResult && (
                  <button
                    onClick={() => setShowFullResult(true)}
                    className="label-mono text-blue-400/80 hover:text-blue-300 mt-1.5 ml-3"
                  >
                    Show full output (+{t.remaining.toLocaleString()} chars) ↓
                  </button>
                )}
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}

// Memoize so non-streaming tool calls inside the same message don't
// re-render when a sibling tool's args/result chunk arrives. The streaming
// block still updates because its result string identity changes.
const ToolCallBlock = memo(ToolCallBlockImpl);
export default ToolCallBlock;
