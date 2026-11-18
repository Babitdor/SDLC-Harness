"use client";

import type { UploadedFile } from "../lib/types";

interface Props {
  files: UploadedFile[];
  onRemove: (index: number) => void;
}

export default function FileChips({ files, onRemove }: Props) {
  if (files.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 px-4 pb-2">
      {files.map((f, i) => (
        <span
          key={f.path}
          className="inline-flex items-center gap-1.5 bg-base-800/80 border border-base-600/50 text-base-300 text-[11px] font-mono rounded px-2.5 py-1 transition-colors hover:border-base-500/50"
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-base-500">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          {f.originalName}
          <button
            onClick={() => onRemove(i)}
            className="text-base-500 hover:text-red-400 transition-colors ml-0.5"
          >
            ✕
          </button>
        </span>
      ))}
    </div>
  );
}