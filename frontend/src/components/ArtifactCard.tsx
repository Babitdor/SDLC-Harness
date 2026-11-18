"use client";

/**
 * A file the agent wrote, rendered inline in the transcript as a clickable
 * card. Clicking opens it in the artifact panel — the same target the
 * inspector's list uses, so there is one preview surface, not two.
 *
 * Before this, a produced file was only reachable by finding it again in the
 * inspector list, even though the message that created it was right there.
 */

/** Extension → the short label shown under the file name. */
const KIND: Record<string, string> = {
  md: "Document",
  markdown: "Document",
  mmd: "Diagram",
  mermaid: "Diagram",
  yaml: "Config",
  yml: "Config",
  feature: "Tests",
  json: "Data",
  html: "Page",
  drawio: "Diagram",
  csv: "Table",
  xlsx: "Spreadsheet",
  py: "Script",
  txt: "Text",
};

function extensionOf(path: string): string {
  const base = path.split("/").pop() || path;
  const dot = base.lastIndexOf(".");
  return dot > 0 ? base.slice(dot + 1).toLowerCase() : "";
}

/**
 * Reduce a tool's `file_path` to the path the artifact API expects.
 *
 * Tools report absolute container paths (`/workspace/current/...`, or the
 * real `/workspace/project_<id>/...` the alias resolves to), while
 * `getArtifactContent` is keyed on the project-relative path. Both prefixes
 * are stripped so a card works regardless of which form the agent used.
 * Returns null for anything outside a project directory — scratch files in
 * /tmp are not artifacts and must not render as deliverables.
 */
export function toArtifactPath(filePath: string): string | null {
  const p = filePath.trim().replace(/\\/g, "/");
  const m = p.match(/^\/workspace\/(?:current|project_[^/]+)\/(.+)$/);
  if (m) return m[1];
  // Already relative, and not an escape attempt or an absolute outsider.
  if (!p.startsWith("/") && !p.includes("..")) return p;
  return null;
}

interface Props {
  /** Project-relative path, e.g. `requirements/REQUIREMENTS.md`. */
  path: string;
  onOpen: (path: string) => void;
}

export default function ArtifactCard({ path, onOpen }: Props) {
  const name = path.split("/").pop() || path;
  const ext = extensionOf(path);
  const kind = KIND[ext] || (ext ? ext.toUpperCase() : "File");
  const dir = path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";

  return (
    <button
      type="button"
      onClick={() => onOpen(path)}
      title={`Open ${path} in the artifact panel`}
      className="group flex w-full items-center gap-3 border border-base-700 bg-base-900/40 px-3 py-2.5 text-left transition-colors hover:border-blue-400/50 hover:bg-blue-400/[0.04]"
    >
      <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center border border-base-700 bg-base-950/60 text-base-500 transition-colors group-hover:border-blue-400/40 group-hover:text-blue-300">
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
          <polyline points="13 2 13 9 20 9" />
        </svg>
      </span>

      <span className="min-w-0 flex-1">
        <span className="block truncate text-[13px] font-medium text-base-200 transition-colors group-hover:text-base-100">
          {name}
        </span>
        <span className="label-mono block truncate text-base-500">
          {kind}
          {dir && ` · ${dir}`}
        </span>
      </span>

      <span className="label-mono flex-shrink-0 text-base-600 transition-colors group-hover:text-blue-300">
        OPEN
      </span>
    </button>
  );
}
