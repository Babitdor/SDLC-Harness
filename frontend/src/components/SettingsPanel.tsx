"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { ModelSettings, ModelSettingsResponse } from "../lib/types";

interface Props {
  /** Visible when the SETTINGS tab is active. */
  active: boolean;
}

/**
 * Settings panel — one section: MODEL (base URL, API key, agent & vision
 * model names), following the "stored override > env var > default" cascade.
 */
export default function SettingsPanel({ active }: Props) {
  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <ModelSettingsSection active={active} />
    </div>
  );
}

// ── Model settings section ──────────────────────────────────────────────

type ModelFormState = { model_provider: string; reasoning_effort: string; base_url: string; agent_model: string; vision_model: string; retry_model: string };

const EMPTY_MODEL_FORM: ModelFormState = {
  model_provider: "",
  reasoning_effort: "",
  base_url: "",
  agent_model: "",
  vision_model: "",
  retry_model: "",
};

function ModelSettingsSection({ active }: Props) {
  const [server, setServer] = useState<ModelSettingsResponse | null>(null);
  const [form, setForm] = useState<ModelFormState>(EMPTY_MODEL_FORM);
  // API key is write-only: never hydrated from the server (it's masked).
  // A non-empty value here means "set this new key" on save.
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const hydrate = useCallback((data: ModelSettingsResponse) => {
    setServer(data);
    setForm({
      model_provider: data.effective.model_provider,
      reasoning_effort: data.effective.reasoning_effort,
      base_url: data.effective.base_url,
      agent_model: data.effective.agent_model,
      vision_model: data.effective.vision_model,
      retry_model: data.effective.retry_model,
    });
    setApiKey("");
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      hydrate(await api.getModelSettings());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [hydrate]);

  useEffect(() => {
    if (active && !server) refresh();
  }, [active, server, refresh]);

  const handleSave = async () => {
    if (!server) return;
    setSaving(true);
    setError(null);
    setStatus(null);
    try {
      const eff = server.effective;
      const diff: import("../lib/types").ModelSettingsUpdate = {};
      (["model_provider", "reasoning_effort", "base_url", "agent_model", "vision_model", "retry_model"] as const).forEach((k) => {
        if (form[k] !== eff[k]) diff[k] = form[k];
      });
      // Only touch the API key when the user typed a new one.
      if (apiKey) diff.api_key = apiKey;
      if (Object.keys(diff).length === 0) {
        setStatus("Nothing changed.");
        setSaving(false);
        return;
      }
      hydrate(await api.updateModelSettings(diff));
      setStatus("Saved. Applies to new chats (existing sessions keep their model).");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const clearApiKey = async () => {
    // Explicitly remove the stored key override.
    setSaving(true);
    setError(null);
    setStatus(null);
    try {
      hydrate(await api.updateModelSettings({ api_key: "" }));
      setStatus("API key override cleared (falls back to env / default).");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const isOverridden = (k: keyof ModelFormState) => Boolean(server?.stored[k]);

  return (
    <>
      <div className="flex-shrink-0 px-5 pt-4 pb-3 border-b border-base-700">
        <div className="label-mono text-blue-500/80 mb-1">MODEL</div>
        <p className="font-display text-[12px] text-base-500 italic leading-snug">
          OpenAI-compatible endpoint + models. Resolution: stored override &gt; env var &gt; default.
        </p>
      </div>

      <div className="px-5 py-4">
        {loading && !server ? (
          <div className="px-3 py-6 text-center">
            <span className="label-mono text-base-600">LOADING…</span>
          </div>
        ) : !server ? (
          <div className="px-3 py-6 text-center">
            <p className="font-display text-sm text-base-400 italic">
              Could not load model settings.
            </p>
            {error && (
              <p className="font-mono text-[11px] text-danger-400 mt-2 break-words">{error}</p>
            )}
            <button
              onClick={refresh}
              className="label-mono mt-3 px-3 py-1.5 border border-base-600 hover:border-blue-500/60 text-base-300 hover:text-blue-300"
            >
              RETRY
            </button>
          </div>
        ) : (
          <div className="space-y-5">
            {/* Model Provider selector */}
            <div>
              <div className="label-mono mb-1.5 flex items-center gap-2">
                <span className="text-base-400">Model provider</span>
                <div className="flex-1 h-px bg-base-700" />
                {isOverridden("model_provider") ? (
                  <span className="text-blue-500/80">OVERRIDE</span>
                ) : (
                  <span className="text-base-600">MODEL_PROVIDER</span>
                )}
              </div>
              <div className="relative">
                <select
                  value={form.model_provider}
                  onChange={(e) => setForm((f) => ({ ...f, model_provider: e.target.value }))}
                  className="w-full px-3 py-2 bg-base-950 border border-base-600 text-base-100 text-[13px] focus:outline-none focus:border-blue-500/60"
                >
                  <option value="openai">OpenAI-compatible</option>
                  <option value="nvidia">NVIDIA AI Endpoints</option>
                </select>
                {isOverridden("model_provider") && (
                  <button
                    onClick={() => setForm((f) => ({ ...f, model_provider: "" }))}
                    className="absolute right-6 top-1/2 -translate-y-1/2 label-mono text-base-500 hover:text-blue-300 px-2 py-0.5"
                    title="Clear override (fall back to env or default)"
                  >
                    CLEAR
                  </button>
                )}
              </div>
              <p className="font-display text-[11px] text-base-500 italic mt-1.5 leading-snug">
                Library/API provider wrapper. Cascade: stored override &gt; env var &gt; default.
              </p>
            </div>

            {/* Reasoning Effort selector */}
            <div>
              <div className="label-mono mb-1.5 flex items-center gap-2">
                <span className="text-base-400">Reasoning effort</span>
                <div className="flex-1 h-px bg-base-700" />
                {isOverridden("reasoning_effort") ? (
                  <span className="text-blue-500/80">OVERRIDE</span>
                ) : (
                  <span className="text-base-600">REASONING_EFFORT</span>
                )}
              </div>
              <div className="relative">
                <select
                  value={form.reasoning_effort}
                  onChange={(e) => setForm((f) => ({ ...f, reasoning_effort: e.target.value }))}
                  className="w-full px-3 py-2 bg-base-950 border border-base-600 text-base-100 text-[13px] focus:outline-none focus:border-blue-500/60"
                >
                  <option value="">default</option>
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
                {isOverridden("reasoning_effort") && (
                  <button
                    onClick={() => setForm((f) => ({ ...f, reasoning_effort: "" }))}
                    className="absolute right-6 top-1/2 -translate-y-1/2 label-mono text-base-500 hover:text-blue-300 px-2 py-0.5"
                    title="Clear override (fall back to env or default)"
                  >
                    CLEAR
                  </button>
                )}
              </div>
              <p className="font-display text-[11px] text-base-500 italic mt-1.5 leading-snug">
                Configures reasoning duration/depth (supported by models like o1, o3-mini).
              </p>
            </div>

            <SettingField
              label="Base URL"
              envName="OPENAI_BASE_URL"
              placeholder={server.effective.base_url}
              value={form.base_url}
              overridden={isOverridden("base_url")}
              onChange={(v) => setForm((f) => ({ ...f, base_url: v }))}
              onReset={() => setForm((f) => ({ ...f, base_url: "" }))}
              hint="Root of the OpenAI-compatible API (unused for NVIDIA AI Endpoints by default)."
            />

            {/* API key — write-only. Masked on the server; type to set. */}
            <div>
              <div className="label-mono mb-1.5 flex items-center gap-2">
                <span className="text-base-400">API key</span>
                <div className="flex-1 h-px bg-base-700" />
                {server.api_key_set ? (
                  <span className="text-blue-500/80">SET</span>
                ) : (
                  <span className="text-base-600">
                    {form.model_provider === "nvidia" ? "NVIDIA_API_KEY" : "OPENAI_API_KEY"}
                  </span>
                )}
              </div>
              <div className="relative">
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={
                    server.api_key_set
                      ? "•••••••• configured — type to replace"
                      : "not set — paste a key to configure"
                  }
                  className="w-full px-3 py-2 bg-base-950 border border-base-600 text-base-100 text-[13px] font-mono focus:outline-none focus:border-blue-500/60"
                />
                {server.api_key_set && (
                  <button
                    onClick={clearApiKey}
                    disabled={saving}
                    className="absolute right-2 top-1/2 -translate-y-1/2 label-mono text-base-500 hover:text-blue-300 px-2 py-0.5 disabled:opacity-40"
                    title="Clear stored key (fall back to env or default)"
                  >
                    CLEAR
                  </button>
                )}
              </div>
              <p className="font-display text-[11px] text-base-500 italic mt-1.5 leading-snug">
                Stored server-side; never displayed back. Shared by the agent and vision models.
              </p>
            </div>

            <SettingField
              label="Agent model"
              envName="AGENT_MODEL"
              placeholder={server.effective.agent_model}
              value={form.agent_model}
              overridden={isOverridden("agent_model")}
              onChange={(v) => setForm((f) => ({ ...f, agent_model: v }))}
              onReset={() => setForm((f) => ({ ...f, agent_model: "" }))}
              hint="Model id used by the orchestrator and all subagents, e.g. Qwen/Qwen3.6-35B-A3B-FP8"
              mono
            />
            <SettingField
              label="Vision model"
              envName="VISION_MODEL"
              placeholder={server.effective.vision_model}
              value={form.vision_model}
              overridden={isOverridden("vision_model")}
              onChange={(v) => setForm((f) => ({ ...f, vision_model: v }))}
              onReset={() => setForm((f) => ({ ...f, vision_model: "" }))}
              hint="Multimodal model for screenshot and image review. Must accept image input."
              mono
            />
            <SettingField
              label="Retry model"
              envName="RETRY_MODEL"
              placeholder={server.effective.retry_model}
              value={form.retry_model}
              overridden={isOverridden("retry_model")}
              onChange={(v) => setForm((f) => ({ ...f, retry_model: v }))}
              onReset={() => setForm((f) => ({ ...f, retry_model: "" }))}
              hint="Fallback model used when the primary model fails (e.g. 501 or rate limits)."
              mono
            />

            {error && (
              <div className="px-3 py-2 border border-danger/40 bg-danger/5">
                <span className="label-mono text-danger-400">ERROR</span>
                <p className="font-mono text-[11px] text-danger-400 mt-1 break-words">{error}</p>
              </div>
            )}
            {status && !error && (
              <div className="px-3 py-2 border border-success/40 bg-success/5">
                <span className="label-mono text-success">OK</span>
                <p className="font-mono text-[11px] text-base-300 mt-1">{status}</p>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2 border-t border-base-700">
              <button
                onClick={refresh}
                disabled={loading}
                className="px-3 py-2 label-mono text-base-400 hover:text-base-100 transition-colors disabled:opacity-40"
              >
                RELOAD
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 label-mono text-blue-300 border border-blue-500/40 hover:border-blue-500/80 hover:bg-blue-500/10 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {saving ? "SAVING…" : "SAVE"}
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

interface FieldProps {
  label: string;
  envName: string;
  placeholder: string;
  value: string;
  overridden: boolean;
  onChange: (v: string) => void;
  onReset: () => void;
  hint: string;
  mono?: boolean;
}

function SettingField({
  label,
  envName,
  placeholder,
  value,
  overridden,
  onChange,
  onReset,
  hint,
  mono,
}: FieldProps) {
  return (
    <div>
      <div className="label-mono mb-1.5 flex items-center gap-2">
        <span className="text-base-400">{label}</span>
        <div className="flex-1 h-px bg-base-700" />
        {overridden ? (
          <span className="text-blue-500/80">OVERRIDE</span>
        ) : (
          <span className="text-base-600">{envName}</span>
        )}
      </div>
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={
            "w-full px-3 py-2 bg-base-950 border border-base-600 text-base-100 text-[13px] focus:outline-none focus:border-blue-500/60 " +
            (mono ? "font-mono" : "")
          }
        />
        {overridden && (
          <button
            onClick={onReset}
            className="absolute right-2 top-1/2 -translate-y-1/2 label-mono text-base-500 hover:text-blue-300 px-2 py-0.5"
            title="Clear override (fall back to env or default)"
          >
            CLEAR
          </button>
        )}
      </div>
      <p className="font-display text-[11px] text-base-500 italic mt-1.5 leading-snug">
        {hint}
      </p>
    </div>
  );
}
