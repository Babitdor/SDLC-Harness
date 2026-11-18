"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CUSTOM_AGENTS_CHANGED_EVENT,
  SUBAGENTS,
  customAgentToInfo,
  type AgentInfo,
  type ArtifactInfo,
} from "../lib/agents";
import { api } from "../lib/api";
import type { CustomAgent, LocalUpload } from "../lib/types";
import MentionDropdown from "./MentionDropdown";
import FileDropdown from "./FileDropdown";
import SlashDropdown, { type SlashCommandInfo } from "./SlashDropdown";

const SLASH_COMMANDS: SlashCommandInfo[] = [
  { name: "compact", desc: "Compact thread history to save context tokens (Claude-style)" },
  { name: "plan", desc: "Run in plan mode to verify goals and ask clarifying questions" },
];

// Paste larger than this collapses into a "PASTED" chip instead of flooding
// the textarea. Either a long single line or many lines qualifies.
const PASTE_MIN_CHARS = 1200;
const PASTE_MIN_LINES = 12;

interface PastedText {
  id: string;
  text: string;
}

interface Props {
  onSend: (message: string) => void;
  onUpload: (files: FileList) => void;
  disabled: boolean;
  streaming?: boolean;
  onAbort?: () => void;
  files?: LocalUpload[];
  onRemoveFile?: (localId: string) => void;
  mentionInsert?: string | null;
  onMentionConsumed?: () => void;
  /** Live workspace artifacts for the active chat — powers the `#` file
   * reference picker. Paths are phase-qualified, e.g. "logical/BDD.md". */
  artifacts?: ArtifactInfo[];
}

export default function ChatInput({
  onSend,
  onUpload,
  disabled,
  streaming = false,
  onAbort,
  files = [],
  onRemoveFile,
  mentionInsert,
  onMentionConsumed,
  artifacts = [],
}: Props) {
  const [value, setValue] = useState("");
  const [mentionFilter, setMentionFilter] = useState("");
  const [mentionActive, setMentionActive] = useState(false);
  const [mentionIndex, setMentionIndex] = useState(0);
  const [customAgents, setCustomAgents] = useState<CustomAgent[]>([]);
  const [slashActive, setSlashActive] = useState(false);
  const [slashFilter, setSlashFilter] = useState("");
  const [slashIndex, setSlashIndex] = useState(0);
  const [fileActive, setFileActive] = useState(false);
  const [fileFilter, setFileFilter] = useState("");
  const [fileIndex, setFileIndex] = useState(0);
  const [pastes, setPastes] = useState<PastedText[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasReadyFiles = files.some((f) => f.kind === "ready");
  const uploading = files.some((f) => f.kind === "pending");

  // Refresh the custom-agent roster from the backend. Called on mount and
  // whenever AgentsPanel dispatches CUSTOM_AGENTS_CHANGED_EVENT after a
  // create/update/delete — so the @mention dropdown stays in sync without
  // a page reload or prop pipe through ChatSidebar.
  const refreshCustomAgents = useCallback(async () => {
    try {
      const data = await api.listCustomAgents();
      setCustomAgents(data.agents);
    } catch {
      // Non-fatal: dropdown just won't suggest custom agents this session.
      // The user can still type @CustomName manually and it'll work — the
      // backend orchestrator is the source of truth.
    }
  }, []);

  useEffect(() => {
    refreshCustomAgents();
    const handler = () => refreshCustomAgents();
    window.addEventListener(CUSTOM_AGENTS_CHANGED_EVENT, handler);
    return () => window.removeEventListener(CUSTOM_AGENTS_CHANGED_EVENT, handler);
  }, [refreshCustomAgents]);

  // The combined roster — built-ins first (for predictable ordering), then
  // user-created subagents mapped into the same shape.
  const allAgents: AgentInfo[] = useMemo(
    () => [...SUBAGENTS, ...customAgents.map(customAgentToInfo)],
    [customAgents]
  );

  // Handle mention insertion from inspector panel
  useEffect(() => {
    if (mentionInsert && textareaRef.current) {
      const el = textareaRef.current;
      const replacement = `@${mentionInsert} `;
      const newValue = value ? `${value} ${replacement}` : replacement;
      setValue(newValue);
      requestAnimationFrame(() => {
        el.focus();
        el.setSelectionRange(newValue.length, newValue.length);
      });
      onMentionConsumed?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mentionInsert]);

  // Auto-resize.
  //
  // The empty state is NOT measured. Measuring it was the bug: on mount
  // `scrollHeight` came back at or above the 160px cap even with no
  // content, so the composer opened ~5 rows tall and only snapped to one
  // row on the first keystroke (the first measurement with real content).
  // Resetting to "auto" and then to "0px" both failed the same way, which
  // is what ruled out the reset value as the cause.
  //
  // An empty textarea has a known-correct height — one row — and `rows={1}`
  // already expresses it. So clear the inline height and let the element
  // size itself; no measurement can get it wrong. Measure only when there
  // is real content to measure, which is the path that already worked.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    if (!value) {
      el.style.height = "";
      return;
    }
    el.style.height = "0px";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, [value]);

  const getFilteredAgents = useCallback(
    () =>
      allAgents.filter((s) =>
        s.name.toLowerCase().startsWith(mentionFilter.toLowerCase())
      ),
    [allAgents, mentionFilter]
  );

  const getFilteredSlashCommands = useCallback(
    () =>
      SLASH_COMMANDS.filter((cmd) =>
        cmd.name.toLowerCase().startsWith(slashFilter.toLowerCase())
      ),
    [slashFilter]
  );

  const getFilteredFiles = useCallback(
    () =>
      artifacts
        .filter((a) => a.name.toLowerCase().includes(fileFilter))
        .slice(0, 50),
    [artifacts, fileFilter]
  );

  const insertMention = useCallback(
    (name: string) => {
      const el = textareaRef.current;
      if (!el) return;
      const pos = el.selectionStart;
      const textBefore = value.substring(0, pos);
      const atIdx = textBefore.lastIndexOf("@");
      const before = value.substring(0, atIdx);
      const after = value.substring(pos);
      const replacement = `@${name} `;
      const newValue = before + replacement + after;
      setValue(newValue);
      setMentionActive(false);
      requestAnimationFrame(() => {
        const newPos = before.length + replacement.length;
        el.setSelectionRange(newPos, newPos);
        el.focus();
      });
    },
    [value]
  );

  const insertSlash = useCallback(
    (name: string) => {
      const el = textareaRef.current;
      if (!el) return;
      const pos = el.selectionStart;
      const textBefore = value.substring(0, pos);
      const slashIdx = textBefore.lastIndexOf("/");
      const before = value.substring(0, slashIdx);
      const after = value.substring(pos);
      const replacement = `/${name} `;
      const newValue = before + replacement + after;
      setValue(newValue);
      setSlashActive(false);
      requestAnimationFrame(() => {
        const newPos = before.length + replacement.length;
        el.setSelectionRange(newPos, newPos);
        el.focus();
      });
    },
    [value]
  );

  const insertFile = useCallback(
    (path: string) => {
      const el = textareaRef.current;
      if (!el) return;
      const pos = el.selectionStart;
      const textBefore = value.substring(0, pos);
      // The `#` begins the current word (detection is word-based), so the
      // last `#` before the cursor marks the token start. The path may
      // contain `/`, so we anchor on `#`, not on whitespace.
      const hashIdx = textBefore.lastIndexOf("#");
      const before = value.substring(0, hashIdx);
      const after = value.substring(pos);
      // Insert as a backticked path so the model reads it unambiguously as a
      // workspace file (it resolves the path with its read_file tool).
      const replacement = "`" + path + "` ";
      const newValue = before + replacement + after;
      setValue(newValue);
      setFileActive(false);
      requestAnimationFrame(() => {
        const newPos = before.length + replacement.length;
        el.setSelectionRange(newPos, newPos);
        el.focus();
      });
    },
    [value]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const val = e.target.value;
      setValue(val);

      // Detect mentions/commands from the CURRENT WORD at the cursor — the
      // chars since the last whitespace. This is more robust than scanning
      // for the rightmost trigger char, because a file token (`#`) may
      // contain `/` (e.g. "#logical/BDD.md") which would otherwise be
      // misread as a slash command.
      const pos = e.target.selectionStart;
      const textBefore = val.substring(0, pos);
      const wsIdx = Math.max(
        textBefore.lastIndexOf(" "),
        textBefore.lastIndexOf("\n"),
        textBefore.lastIndexOf("\t")
      );
      const word = textBefore.substring(wsIdx + 1);
      const trigger = word.charAt(0);
      const body = word.substring(1);

      if (trigger === "@") {
        setMentionFilter(body.toLowerCase());
        setMentionActive(true);
        setMentionIndex(0);
        setSlashActive(false);
        setFileActive(false);
        return;
      }
      if (trigger === "#") {
        setFileFilter(body.toLowerCase());
        setFileActive(true);
        setFileIndex(0);
        setMentionActive(false);
        setSlashActive(false);
        return;
      }
      if (trigger === "/") {
        setSlashFilter(body.toLowerCase());
        setSlashActive(true);
        setSlashIndex(0);
        setMentionActive(false);
        setFileActive(false);
        return;
      }
      setMentionActive(false);
      setSlashActive(false);
      setFileActive(false);
    },
    []
  );

  // Large pastes collapse into a chip rather than dumping into the textarea.
  // Small pastes fall through to the default (insert into the field).
  const handlePaste = useCallback((e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const text = e.clipboardData.getData("text");
    if (!text) return;
    const lineCount = text.split("\n").length;
    if (text.length >= PASTE_MIN_CHARS || lineCount >= PASTE_MIN_LINES) {
      e.preventDefault();
      setPastes((prev) => [...prev, { id: crypto.randomUUID(), text }]);
    }
  }, []);

  const removePaste = useCallback((id: string) => {
    setPastes((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (disabled) return;
    if (uploading) return;
    if (!trimmed && !hasReadyFiles && pastes.length === 0) return;
    // Typed message first so leading @mentions and /slash-commands keep their
    // position, then each pasted block as context.
    const pasteBlocks = pastes.map((p) => p.text.trim()).filter(Boolean);
    const combined = [trimmed, ...pasteBlocks].filter(Boolean).join("\n\n");
    onSend(combined);
    setValue("");
    setPastes([]);
  }, [value, disabled, uploading, hasReadyFiles, pastes, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (mentionActive) {
        const filtered = getFilteredAgents();
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setMentionIndex((i) => (i + 1) % filtered.length);
          return;
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          setMentionIndex((i) => (i - 1 + filtered.length) % filtered.length);
          return;
        }
        if (e.key === "Enter" || e.key === "Tab") {
          e.preventDefault();
          if (filtered.length > 0) insertMention(filtered[mentionIndex].name);
          return;
        }
        if (e.key === "Escape") {
          setMentionActive(false);
          return;
        }
      }

      if (fileActive) {
        const filtered = getFilteredFiles();
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setFileIndex((i) => (filtered.length ? (i + 1) % filtered.length : 0));
          return;
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          setFileIndex((i) =>
            filtered.length ? (i - 1 + filtered.length) % filtered.length : 0
          );
          return;
        }
        if (e.key === "Enter" || e.key === "Tab") {
          if (filtered.length > 0) {
            e.preventDefault();
            insertFile(filtered[fileIndex].name);
            return;
          }
          // No matches — fall through so Enter still sends the message.
        }
        if (e.key === "Escape") {
          setFileActive(false);
          return;
        }
      }

      if (slashActive) {
        const filtered = getFilteredSlashCommands();
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setSlashIndex((i) => (i + 1) % filtered.length);
          return;
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          setSlashIndex((i) => (i - 1 + filtered.length) % filtered.length);
          return;
        }
        if (e.key === "Enter" || e.key === "Tab") {
          e.preventDefault();
          if (filtered.length > 0) insertSlash(filtered[slashIndex].name);
          return;
        }
        if (e.key === "Escape") {
          setSlashActive(false);
          return;
        }
      }

      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [mentionActive, mentionIndex, getFilteredAgents, insertMention, fileActive, fileIndex, getFilteredFiles, insertFile, slashActive, slashIndex, getFilteredSlashCommands, insertSlash, handleSend]
  );

  const sendDisabled =
    disabled || uploading || (!value.trim() && !hasReadyFiles && pastes.length === 0);

  return (
    <div className="relative px-6 py-4 border-t border-base-700 bg-base-950/80 backdrop-blur-sm">
      {/* Mention dropdown floats above the composer */}
      <MentionDropdown
        items={getFilteredAgents()}
        activeIndex={mentionIndex}
        onSelect={insertMention}
        visible={mentionActive}
      />

      {/* Workspace file reference dropdown floats above the composer */}
      <FileDropdown
        items={getFilteredFiles()}
        activeIndex={fileIndex}
        onSelect={insertFile}
        visible={fileActive}
      />

      {/* Slash commands dropdown floats above the composer */}
      <SlashDropdown
        items={getFilteredSlashCommands()}
        activeIndex={slashIndex}
        onSelect={insertSlash}
        visible={slashActive}
      />

      {/* Composer plate — Composer plate. The
          frame stays steady; the focus state lights up the amber tick
          accent at the corners instead of a generic blue ring. */}
      <div className={
        "relative border bg-base-900/70 transition-all overflow-hidden " +
        "border-base-600 focus-within:border-blue-400/60"
      }>
        {(files.length > 0 || pastes.length > 0) && (
          <div className="flex flex-wrap gap-2 px-3 pt-3 pb-2 border-b border-base-700">
            {pastes.map((p) => (
              <PasteChip key={p.id} text={p.text} onRemove={() => removePaste(p.id)} />
            ))}
            {files.map((f) => (
              <FileChip
                key={f.localId}
                file={f}
                onRemove={() => onRemoveFile?.(f.localId)}
              />
            ))}
          </div>
        )}

        <div className="flex items-end gap-2 px-3 py-2.5">
          {/* Attach — drafting clip, hairline button, mono micro-label.
              Box style instead of round so it matches the language. */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className="flex-shrink-0 w-9 h-9 flex items-center justify-center border border-base-700 text-base-400 hover:text-blue-300 hover:border-blue-400/50 transition-all disabled:opacity-30"
            title="Attach files"
            type="button"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.xlsx,.xls,.docx,.doc,.csv,.txt,.md,.py,.json,.png,.jpg,.jpeg,.gif"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.length) onUpload(e.target.files);
              e.target.value = "";
            }}
          />

          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            onBlur={() => {
              setMentionActive(false);
              setFileActive(false);
              setSlashActive(false);
            }}
            disabled={disabled}
            placeholder="Write to the harness…  @ summon a specialist · # reference a file"
            rows={1}
            className="flex-1 bg-transparent border-0 px-2 py-2 text-[14px] text-base-100 placeholder:text-base-500/70 focus:outline-none resize-none max-h-40 overflow-y-auto disabled:opacity-30"
          />

          {/* Stop / Send Button — Stop when streaming, Send otherwise (solid blue when armed, hollow when not) */}
          {streaming ? (
            <button
              onClick={onAbort}
              className="flex-shrink-0 px-4 h-9 flex items-center gap-2 border border-danger bg-danger text-base-950 hover:bg-danger-400 hover:border-danger-400 active:scale-95 transition-all duration-150 rounded-sm"
              title="Stop Agent"
              type="button"
            >
              <span className="label-mono font-semibold">STOP</span>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                <rect x="4" y="4" width="16" height="16" rx="1" />
              </svg>
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={sendDisabled}
              className={
                "flex-shrink-0 px-4 h-9 flex items-center gap-2 border transition-all duration-150 disabled:opacity-30 disabled:cursor-not-allowed " +
                (sendDisabled
                  ? "border-base-700 text-base-500"
                  : "border-blue-400 bg-blue-400 text-base-950 hover:bg-blue-300 active:scale-95")
              }
              title={uploading ? "Waiting for upload to finish…" : "Send"}
              type="button"
            >
              <span className="label-mono">SEND</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Hint rail — small mono cue below the composer, like a footnote */}
      <div className="flex items-center justify-between mt-2.5 px-1">
        <span className="label-mono text-base-600 flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <kbd className="px-1.5 py-0.5 border border-base-700 bg-base-800 text-[9px] leading-none">⏎</kbd>
            <span>Send</span>
          </span>
          <span className="w-px h-3 bg-base-700" />
          <span className="flex items-center gap-1.5">
            <kbd className="px-1.5 py-0.5 border border-base-700 bg-base-800 text-[9px] leading-none">⇧⏎</kbd>
            <span>New line</span>
          </span>
          <span className="w-px h-3 bg-base-700" />
          <span className="flex items-center gap-1.5">
            <kbd className="px-1.5 py-0.5 border border-base-700 bg-base-800 text-[9px] leading-none">@</kbd>
            <span>Summon agent</span>
          </span>
          <span className="w-px h-3 bg-base-700" />
          <span className="flex items-center gap-1.5">
            <kbd className="px-1.5 py-0.5 border border-base-700 bg-base-800 text-[9px] leading-none">#</kbd>
            <span>Reference file</span>
          </span>
        </span>
        <div className="flex items-center gap-4 flex-shrink-0">
          {uploading && (
            <span className="label-mono text-blue-400/80 flex items-center gap-2">
              <div className="w-2 h-2 border border-blue-400 border-t-transparent rounded-full animate-spin" />
              UPLOADING
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Chip ─────────────────────────────────────────────────────────────────

function FileChip({
  file,
  onRemove,
}: {
  file: LocalUpload;
  onRemove: () => void;
}) {
  const label =
    file.kind === "ready" ? file.original_name : file.name;

  const baseCls =
    "inline-flex items-center gap-2 font-mono text-[11px] px-2.5 py-1 border transition-colors";

  if (file.kind === "pending") {
    return (
      <span
        className={`${baseCls} bg-base-900/80 border-blue-400/40 text-base-300`}
        title="Uploading…"
      >
        <div className="w-2.5 h-2.5 border border-blue-400 border-t-transparent rounded-full animate-spin" />
        {label}
        <button
          onClick={onRemove}
          className="text-base-500 hover:text-danger transition-colors"
          type="button"
          title="Cancel"
        >
          ×
        </button>
      </span>
    );
  }

  if (file.kind === "error") {
    return (
      <span
        className={`${baseCls} bg-danger/10 border-danger/40 text-danger-400`}
        title={file.message}
      >
        <span className="font-mono text-xs">!</span>
        {label}
        <button
          onClick={onRemove}
          className="text-danger-400/60 hover:text-danger-400 transition-colors"
          type="button"
          title="Dismiss"
        >
          ×
        </button>
      </span>
    );
  }

  // ready — small filled square (drafting "registered" mark)
  return (
    <span
      className={`${baseCls} bg-base-900/80 border-base-600 text-base-200 hover:border-blue-400/50`}
    >
      <span className="w-2 h-2 bg-success" />
      {label}
      <button
        onClick={onRemove}
        className="text-base-500 hover:text-danger transition-colors"
        type="button"
        title="Remove"
      >
        ×
      </button>
    </span>
  );
}

// ── Pasted-text chip ───────────────────────────────────────────────────────
// A large paste collapses into this card: a faded preview + a PASTED badge +
// line count. Clicking the card opens a modal with the full text; the × on the
// corner removes it.

function PasteChip({ text, onRemove }: { text: string; onRemove: () => void }) {
  const [open, setOpen] = useState(false);

  const lineCount = useMemo(() => text.split("\n").length, [text]);
  const preview = useMemo(() => text.trim().slice(0, 240), [text]);

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen(true);
          }
        }}
        title="Click to preview pasted text"
        className="group relative w-[150px] h-[92px] border border-base-600 bg-base-900/80 overflow-hidden flex flex-col cursor-pointer hover:border-blue-400/50 transition-colors text-left"
      >
        {/* Preview text, fading out at the bottom */}
        <div className="flex-1 px-2 py-1.5 text-[9.5px] leading-snug text-base-400 whitespace-pre-wrap break-words overflow-hidden">
          {preview}
        </div>
        <div className="pointer-events-none absolute inset-x-0 top-6 bottom-7 bg-gradient-to-b from-transparent to-base-900/90" />

        {/* Footer: PASTED badge + line count */}
        <div className="relative flex items-center justify-between px-2 py-1 border-t border-base-700 bg-base-900">
          <span className="label-mono text-[9px] bg-base-800 border border-base-600 px-1.5 py-0.5 text-base-300">
            PASTED
          </span>
          <span className="label-mono text-[9px] text-base-500 tabular-nums">
            {lineCount.toLocaleString()} {lineCount === 1 ? "line" : "lines"}
          </span>
        </div>

        {/* Remove — stops the click from opening the preview */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="absolute top-1 right-1 w-4 h-4 flex items-center justify-center bg-base-950/70 text-base-400 hover:text-danger opacity-0 group-hover:opacity-100 transition-opacity"
          type="button"
          title="Remove"
        >
          ×
        </button>
      </div>

      {open && <PastePreviewModal text={text} onClose={() => setOpen(false)} />}
    </>
  );
}

function PastePreviewModal({ text, onClose }: { text: string; onClose: () => void }) {
  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const charCount = text.length;
  const lineCount = text.split("\n").length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-base-950/70 backdrop-blur-sm p-6"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[80vh] flex flex-col border border-base-600 bg-base-900 shadow-2xl shadow-base-950/50"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-base-700">
          <span className="label-mono text-[10px] bg-base-800 border border-base-600 px-1.5 py-0.5 text-base-300">
            PASTED
          </span>
          <span className="label-mono text-[10px] text-base-500 tabular-nums">
            {charCount.toLocaleString()} chars · {lineCount.toLocaleString()}{" "}
            {lineCount === 1 ? "line" : "lines"}
          </span>
          <div className="flex-1" />
          <button
            onClick={onClose}
            className="label-mono text-[11px] text-base-400 hover:text-base-100 transition-colors px-2 py-1"
            type="button"
            title="Close (Esc)"
          >
            CLOSE ✕
          </button>
        </div>
        <pre className="flex-1 overflow-auto px-4 py-3 font-mono text-[12px] text-base-200 whitespace-pre-wrap break-words leading-relaxed">
          {text}
        </pre>
      </div>
    </div>
  );
}
