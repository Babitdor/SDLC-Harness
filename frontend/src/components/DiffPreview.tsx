"use client";

import { useMemo, useState } from "react";
import { diffLines, type Change } from "diff";

interface DiffPreviewProps {
  /** Current content on disk (the "before"). */
  oldContent: string;
  /** Proposed or resulting content (the "after"). */
  newContent: string;
  /** Optional filename to show in the header. */
  filename?: string;
}

// ── Helpers ────────────────────────────────────────────────────────────

interface DiffLine {
  kind: "add" | "remove" | "context";
  content: string;
  oldLine: number | null;
  newLine: number | null;
}

function computeLines(oldStr: string, newStr: string): DiffLine[] {
  const changes: Change[] = diffLines(oldStr, newStr);
  const lines: DiffLine[] = [];
  let oldLine = 1;
  let newLine = 1;

  for (const change of changes) {
    const parts = change.value.split("\n");
    // The last element after splitting on \n is always "" — skip it
    // unless the value itself is empty (edge case).
    const actualParts = change.value.endsWith("\n")
      ? parts.slice(0, -1)
      : parts;

    if (change.added) {
      for (const line of actualParts) {
        lines.push({ kind: "add", content: line, oldLine: null, newLine: newLine++ });
      }
    } else if (change.removed) {
      for (const line of actualParts) {
        lines.push({ kind: "remove", content: line, oldLine: oldLine++, newLine: null });
      }
    } else {
      for (const line of actualParts) {
        lines.push({ kind: "context", content: line, oldLine: oldLine++, newLine: newLine++ });
      }
    }
  }

  return lines;
}

// ── Truncation ─────────────────────────────────────────────────────────

const MAX_DIFF_LINES = 200;

// ── Diff line styling helpers ──────────────────────────────────────────

interface DiffLineStyle {
  bg: string;
  textColor: string;
  prefix: string;
}

function diffLineStyle(kind: DiffLine["kind"]): DiffLineStyle {
  switch (kind) {
    case "add":
      return { bg: "bg-green-950/30", textColor: "text-green-300", prefix: "+" };
    case "remove":
      return { bg: "bg-red-950/30", textColor: "text-red-300", prefix: "−" };
    default:
      return { bg: "", textColor: "text-base-300", prefix: " " };
  }
}

function diffLineNumber(line: DiffLine): string {
  switch (line.kind) {
    case "add":
      return `+${line.newLine}`;
    case "remove":
      return `-${line.oldLine}`;
    default:
      return `${line.oldLine}`;
  }
}

// ── Component ──────────────────────────────────────────────────────────

export default function DiffPreview({ oldContent, newContent, filename }: DiffPreviewProps) {
  const [showFull, setShowFull] = useState(false);

  const lines = useMemo(() => computeLines(oldContent, newContent), [oldContent, newContent]);

  const addCount = lines.filter((l) => l.kind === "add").length;
  const removeCount = lines.filter((l) => l.kind === "remove").length;
  const hasChanges = addCount > 0 || removeCount > 0;
  const truncated = lines.length > MAX_DIFF_LINES && !showFull;
  const visibleLines = truncated ? lines.slice(0, MAX_DIFF_LINES) : lines;

  if (!oldContent && !newContent) {
    return (
      <div className="px-3 py-2 border border-base-700 bg-base-950/30">
        <span className="label-mono text-base-500">— empty —</span>
      </div>
    );
  }

  if (!hasChanges) {
    return (
      <div className="px-3 py-2 border border-base-700 bg-base-950/30">
        <span className="label-mono text-base-500">— no changes —</span>
      </div>
    );
  }

  return (
    <div className="border border-base-700 bg-base-950/40 overflow-hidden">
      {/* Header — filename + change summary */}
      <div className="flex items-center gap-3 px-3 py-1.5 border-b border-base-700 bg-base-900/60">
        {filename && (
          <span className="font-mono text-[11px] text-cyan-300 truncate flex-1">
            {filename}
          </span>
        )}
        <span className="label-mono text-success tabular-nums">
          +{addCount}
        </span>
        <span className="label-mono text-danger-400 tabular-nums">
          -{removeCount}
        </span>
        <span className="label-mono text-base-600 tabular-nums">
          {lines.length} lines
        </span>
      </div>

      {/* Diff body */}
      <div className="overflow-x-auto">
        <table className="w-full font-mono text-[11px] leading-relaxed border-collapse">
          <tbody>
            {visibleLines.map((line, i) => {
              const { bg, textColor, prefix } = diffLineStyle(line.kind);
              const lineNum = diffLineNumber(line);
              return (
                <tr key={i} className={bg}>
                  <td className="w-12 text-right pr-2 select-none text-base-600 tabular-nums border-r border-base-700/50">
                    {lineNum ?? ""}
                  </td>
                  <td className="w-4 text-center select-none text-base-600">
                    {prefix}
                  </td>
                  <td className={`whitespace-pre-wrap break-words pl-2 ${textColor}`}>
                    {line.content}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Truncation notice */}
      {truncated && (
        <div className="px-3 py-2 border-t border-blue-500/40 bg-blue-500/[0.04] flex flex-col gap-2">
          <div className="label-mono text-blue-500/80">
            TRUNCATED · {lines.length - MAX_DIFF_LINES} LINES HIDDEN
          </div>
          <button
            onClick={() => setShowFull(true)}
            className="self-start label-mono px-3 py-1 border border-blue-500/60 bg-blue-500/10 text-blue-300 hover:bg-blue-500/20 transition-all"
          >
            SHOW FULL DIFF ↓
          </button>
        </div>
      )}
    </div>
  );
}
