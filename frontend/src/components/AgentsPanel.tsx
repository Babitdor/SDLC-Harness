"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { CUSTOM_AGENTS_CHANGED_EVENT, SUBAGENTS } from "../lib/agents";
import type { CustomAgent, ToolRegistryResponse } from "../lib/types";

interface Props {
  /** Visible when the AGENTS tab is active. */
  active: boolean;
}

interface EditorState {
  open: boolean;
  /** null = create mode; otherwise the agent being edited. */
  agent: CustomAgent | null;
}

const EMPTY_EDITOR: EditorState = { open: false, agent: null };

export default function AgentsPanel({ active }: Props) {
  const [customAgents, setCustomAgents] = useState<CustomAgent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editor, setEditor] = useState<EditorState>(EMPTY_EDITOR);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listCustomAgents();
      setCustomAgents(data.agents);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Only fetch when the tab becomes active — avoids a wasted request on first render.
    if (active) refresh();
  }, [active, refresh]);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!confirm("Delete this agent? It will disappear from every chat on the next message.")) {
        return;
      }
      try {
        await api.deleteCustomAgent(id);
        setCustomAgents((prev) => prev.filter((a) => a.id !== id));
        window.dispatchEvent(new CustomEvent(CUSTOM_AGENTS_CHANGED_EVENT));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    },
    []
  );

  return (
    <>
      {/* New-agent action sits in the sticky header area */}
      <div className="flex-shrink-0 px-5 pt-4 pb-3 border-b border-base-700">
        <button
          onClick={() => setEditor({ open: true, agent: null })}
          className="group w-full flex items-center justify-between px-3 py-2.5
                     border border-base-600 hover:border-blue-500/60
                     bg-base-800/40 hover:bg-base-800/80
                     transition-all duration-200 relative
                     tick-corners"
        >
          <span className="label-mono text-base-300 group-hover:text-blue-300 transition-colors">
            + NEW AGENT
          </span>
          <span className="font-mono text-[10px] text-base-500 group-hover:text-blue-500/70 transition-colors">
            ↵
          </span>
        </button>
        <p className="font-display text-[12px] text-base-500 italic mt-2 leading-snug">
          Live — applies to your next message in any chat.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4">
        {/* Built-ins (read-only) */}
        <div className="label-mono text-base-500 px-2 mb-3 flex items-center gap-2">
          <span>BUILT-IN</span>
          <div className="flex-1 h-px bg-base-700" />
          <span className="text-base-600 tabular-nums">
            {SUBAGENTS.length.toString().padStart(2, "0")}
          </span>
        </div>
        <div className="space-y-1 mb-6">
          {SUBAGENTS.map((a) => (
            <div
              key={a.name}
              className="pl-4 pr-3 py-2 border-l-2 border-transparent"
            >
              <div className="flex items-center gap-2">
                <span className="text-[14px]">{a.icon}</span>
                <span className="text-[13px] text-base-300 font-medium">{a.name}</span>
                <span data-phase={a.phase} className="phase-code ml-auto">
                  P{a.phase.toString().padStart(2, "0")}
                </span>
              </div>
              <p className="font-display text-[12px] text-base-500 mt-1 leading-snug">
                {a.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Custom agents */}
        <div className="label-mono text-base-500 px-2 mb-3 flex items-center gap-2">
          <span>CUSTOM</span>
          <div className="flex-1 h-px bg-base-700" />
          <span className="text-base-600 tabular-nums">
            {customAgents.length.toString().padStart(2, "0")}
          </span>
        </div>

        {error && (
          <div className="px-3 py-2 mb-3 border border-danger/40 bg-danger/5">
            <span className="label-mono text-danger-400">ERROR</span>
            <p className="font-mono text-[11px] text-danger-400 mt-1 break-words">
              {error}
            </p>
          </div>
        )}

        {loading && customAgents.length === 0 ? (
          <div className="px-3 py-4 text-center">
            <span className="label-mono text-base-600">LOADING…</span>
          </div>
        ) : customAgents.length === 0 && !error ? (
          <div className="px-3 py-6 text-center">
            <p className="font-display text-sm text-base-400 italic">
              No custom agents yet.
            </p>
            <p className="label-mono text-base-600 mt-2">
              CREATE ONE ABOVE
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {customAgents.map((a) => (
              <div key={a.id} className="group relative">
                <button
                  onClick={() => setEditor({ open: true, agent: a })}
                  className="w-full text-left pl-4 pr-16 py-2.5 transition-all duration-150 relative border-l-2 border-transparent hover:border-base-500 hover:bg-base-800/40"
                >
                  <div className="text-[13px] leading-tight text-base-300 group-hover:text-base-100 font-medium truncate">
                    {a.name}
                  </div>
                  <p className="font-display text-[12px] text-base-500 mt-1 leading-snug line-clamp-2">
                    {a.description || <em className="italic">No description</em>}
                  </p>
                  {a.tools && a.tools.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {a.tools.map((t) => (
                        <span
                          key={t}
                          className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-blue-400/20 bg-blue-400/5 text-blue-300/70 uppercase tracking-wider"
                        >
                          {t.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  )}
                </button>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(a.id);
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 transition-all opacity-0 group-hover:opacity-100 text-base-600 hover:text-danger"
                  title="Delete agent"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {editor.open && (
        <AgentEditor
          initial={editor.agent}
          onClose={() => setEditor(EMPTY_EDITOR)}
          onSaved={(saved) => {
            setCustomAgents((prev) => {
              const idx = prev.findIndex((p) => p.id === saved.id);
              if (idx === -1) return [...prev, saved];
              const copy = [...prev];
              copy[idx] = saved;
              return copy;
            });
            // Notify ChatInput (and any other listener) so the @mention
            // dropdown picks up the new/updated agent without a reload.
            window.dispatchEvent(new CustomEvent(CUSTOM_AGENTS_CHANGED_EVENT));
            setEditor(EMPTY_EDITOR);
          }}
        />
      )}
    </>
  );
}


// ── Create / edit modal ────────────────────────────────────────────────

interface EditorProps {
  initial: CustomAgent | null;
  onClose: () => void;
  onSaved: (saved: CustomAgent) => void;
}

function AgentEditor({ initial, onClose, onSaved }: EditorProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [systemPrompt, setSystemPrompt] = useState(initial?.system_prompt ?? "");
  const [selectedTools, setSelectedTools] = useState<string[]>(initial?.tools ?? []);
  const [registry, setRegistry] = useState<ToolRegistryResponse | null>(null);
  const [registryLoading, setRegistryLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = initial !== null;
  const canSave = name.trim() && description.trim() && systemPrompt.trim() && !saving;

  // Fetch tool registry on mount
  useEffect(() => {
    setRegistryLoading(true);
    api.getToolRegistry()
      .then(setRegistry)
      .catch(() => {
        // Registry fetch is non-critical — user can still save without tools
        setRegistry(null);
      })
      .finally(() => setRegistryLoading(false));
  }, []);

  const toggleTool = (key: string) => {
    setSelectedTools((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const body = {
        name: name.trim(),
        description: description.trim(),
        system_prompt: systemPrompt,
        tools: selectedTools.length > 0 ? selectedTools : undefined,
      };
      const saved = isEdit
        ? await api.updateCustomAgent(initial!.id, body)
        : await api.createCustomAgent(body);
      onSaved(saved);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[60] bg-base-950/85 backdrop-blur-sm flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[90vh] flex flex-col bg-base-900 border border-base-600 tick-corners"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-base-700">
          <div>
            <span className="label-mono text-blue-500/80">
              {isEdit ? "EDIT AGENT" : "NEW AGENT"}
            </span>
            <h2 className="font-display text-[18px] text-base-100 mt-1">
              {isEdit ? initial!.name : "Define a subagent"}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-base-400 hover:text-base-100 transition-colors p-1"
            aria-label="Close"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <Field label="Name" hint="Lowercased + dashed for the agent ID (e.g. 'Research Helper' → research-helper). Cannot collide with a built-in.">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Research Helper"
              className="w-full px-3 py-2 bg-base-950 border border-base-600 text-base-100 font-mono text-[13px] focus:outline-none focus:border-blue-500/60"
              maxLength={64}
            />
          </Field>

          <Field label="Description" hint="Shown to the orchestrator so it knows when to delegate to this agent.">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="One- or two-sentence summary of what this agent does and when to invoke it."
              className="w-full px-3 py-2 bg-base-950 border border-base-600 text-base-100 text-[13px] focus:outline-none focus:border-blue-500/60 resize-y min-h-[60px]"
              maxLength={2000}
              rows={3}
            />
          </Field>

          <Field label="System prompt" hint="The full instructions the agent runs under. Inherits default tools: read_file, write_file, ls, execute.">
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="You are an agent that..."
              className="w-full px-3 py-2 bg-base-950 border border-base-600 text-base-100 font-mono text-[12px] focus:outline-none focus:border-blue-500/60 resize-y min-h-[200px] leading-relaxed"
              maxLength={50000}
              rows={12}
            />
          </Field>

          {/* Tool selection */}
          <Field
            label="TOOLS"
            hint="Domain tools this agent can use. Unavailable tools (greyed out) are missing runtime dependencies."
          >
            {registryLoading && (
              <div className="px-3 py-4 text-center">
                <span className="label-mono text-base-600">LOADING TOOLS…</span>
              </div>
            )}
            {!registryLoading && !registry && (
              <div className="px-3 py-2 border border-base-700 bg-base-800/20">
                <span className="label-mono text-base-500">UNAVAILABLE</span>
                <p className="font-mono text-[11px] text-base-500 mt-1">
                  Could not fetch tool registry. Save without tools and try again.
                </p>
              </div>
            )}
            {registry && (
              <div className="space-y-1 max-h-[240px] overflow-y-auto border border-base-700 bg-base-950/50 p-2">
                {Object.entries(registry.categories).map(([key, entry]) => {
                  const isSelected = selectedTools.includes(key);
                  const disabled = !entry.available;
                  return (
                    <label
                      key={key}
                      className={
                        "flex items-start gap-3 px-3 py-2 cursor-pointer transition-all rounded " +
                        (disabled
                          ? "opacity-40 cursor-not-allowed"
                          : isSelected
                            ? "bg-blue-400/10 border border-blue-400/30"
                            : "hover:bg-base-800/40 border border-transparent")
                      }
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        disabled={disabled}
                        onChange={() => toggleTool(key)}
                        className="mt-0.5 accent-blue-500"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[13px] text-base-200 font-medium">
                            {entry.label}
                          </span>
                          {disabled && (
                            <span className="text-[9px] font-mono px-1 py-0.5 rounded border border-base-700 bg-base-800/40 text-base-500 uppercase">
                              UNAVAILABLE
                            </span>
                          )}
                        </div>
                        <p className="font-display text-[11px] text-base-500 mt-0.5 leading-snug">
                          {entry.description}
                        </p>
                      </div>
                    </label>
                  );
                })}
              </div>
            )}
          </Field>

          {error && (
            <div className="px-3 py-2 border border-danger/40 bg-danger/5">
              <span className="label-mono text-danger-400">ERROR</span>
              <p className="font-mono text-[11px] text-danger-400 mt-1 break-words">{error}</p>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 px-5 py-3 border-t border-base-700">
          <button
            onClick={onClose}
            className="px-4 py-2 label-mono text-base-400 hover:text-base-100 transition-colors"
          >
            CANCEL
          </button>
          <button
            onClick={handleSave}
            disabled={!canSave}
            className="px-4 py-2 label-mono text-blue-300 border border-blue-500/40 hover:border-blue-500/80 hover:bg-blue-500/10 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:border-blue-500/40"
          >
            {saving ? "SAVING…" : isEdit ? "SAVE CHANGES" : "CREATE AGENT"}
          </button>
        </div>
      </div>
    </div>
  );
}


function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="label-mono text-base-400 mb-1.5 flex items-center gap-2">
        <span>{label}</span>
        <div className="flex-1 h-px bg-base-700" />
      </div>
      {children}
      {hint && (
        <p className="font-display text-[11px] text-base-500 italic mt-1.5 leading-snug">
          {hint}
        </p>
      )}
    </div>
  );
}
