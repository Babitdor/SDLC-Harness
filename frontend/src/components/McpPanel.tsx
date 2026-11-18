"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { SUBAGENTS } from "../lib/agents";
import type {
  McpServerOut,
  McpServerStatus,
  McpServersResponse,
  McpTestResponse,
  McpTransport,
} from "../lib/types";

interface Props {
  /** Visible when the MCP tab is active. */
  active: boolean;
}

interface FormState {
  id: string | null;
  name: string;
  transport: McpTransport;
  enabled: boolean;
  command: string;
  args: string;
  url: string;
  /** New/changed "KEY: value" lines. Only these keys are written. */
  credentials: string;
  /** What this server expects, e.g. "Authorization: Bearer <PAT>". */
  hint: string;
  /** Keys already stored (values are write-only, so only names come back). */
  existingKeys: string[];
  agents: string[];
}

const EMPTY_FORM: FormState = {
  id: null,
  name: "",
  transport: "http",
  enabled: true,
  command: "uvx",
  args: "",
  url: "",
  credentials: "",
  hint: "",
  existingKeys: [],
  agents: [],
};

/** Backend agent keys are the lower-cased roster names (ingestion, api, …). */
const agentKey = (name: string) => name.toLowerCase();

/** Parse "KEY: value" / "KEY=value" lines into a credential map. */
function parseCredentials(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split("\n")) {
    if (!line.trim()) continue;
    const match = line.match(/^\s*([^:=\s][^:=]*?)\s*[:=]\s*(.+?)\s*$/);
    if (!match) throw new Error("Use KEY: value or KEY=value for each credential.");
    out[match[1]] = match[2];
  }
  return out;
}

function ServerRow({
  server,
  status,
  testResult,
  testing,
  onTest,
  onEdit,
  onDelete,
  onToggle,
  onConnect,
  connecting,
}: {
  server: McpServerOut;
  status: McpServerStatus | undefined;
  testResult: McpTestResponse | undefined;
  testing: boolean;
  onTest: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onToggle: () => void;
  onConnect: () => void;
  connecting: boolean;
}) {
  const ok = status?.ok;
  return (
    <div className="border border-base-700 bg-base-900/20 px-3 py-2.5">
      {/* Name gets its own line: at ~260px the four actions would otherwise
          squeeze it to zero width (flex-shrink-0 wins over truncate). */}
      <div className="flex items-center gap-2">
        <span
          className={
            "w-1.5 h-1.5 flex-shrink-0 rounded-full " +
            (status === undefined
              ? "bg-base-600"
              : ok
                ? "bg-blue-400"
                : "bg-red-500/80")
          }
          title={status === undefined ? "not loaded" : ok ? "connected" : "failed"}
        />
        <span className="text-[12px] text-base-200 font-medium truncate flex-1 min-w-0">{server.name}</span>
        <span className="label-mono text-base-600 flex-shrink-0">{server.transport}</span>
        {!server.enabled && <span className="label-mono text-base-600 flex-shrink-0">OFF</span>}
        {!server.enabled && server.transport === "http" && server.header_keys.length === 0 && !server.oauth_connected && (
          <span className="label-mono text-amber-400/80 flex-shrink-0" title="Paste a credential header, then enable">
            AUTH
          </span>
        )}
      </div>

      {server.description && (
        <p className="mt-1 text-[10.5px] leading-snug text-base-500">{server.description}</p>
      )}
      {!server.enabled && server.credential_hint && (
        <p className="mt-1 font-mono text-[10px] text-amber-400/70 truncate" title={server.credential_hint}>
          needs {server.credential_hint}
        </p>
      )}

      <div className="mt-1.5 flex items-center gap-2">
        {server.transport === "http" && (
          <button onClick={onConnect} disabled={connecting}
            title="Sign in with OAuth; use EDIT for an API key or bearer token"
            className="label-mono text-base-400 hover:text-blue-300 disabled:opacity-40">
            {connecting ? "CONNECTING…" : server.oauth_connected ? "RECONNECT" : "CONNECT"}
          </button>
        )}
        <button
          onClick={onToggle}
          className="label-mono text-base-500 hover:text-base-200 transition-colors"
          title={server.enabled ? "Disable this server" : "Enable this server"}
        >
          {server.enabled ? "DISABLE" : "ENABLE"}
        </button>
        <button
          onClick={onTest}
          disabled={testing}
          className="label-mono text-base-400 hover:text-blue-300 transition-colors disabled:opacity-40"
        >
          {testing ? "TESTING…" : "TEST"}
        </button>
        <button onClick={onEdit} className="label-mono text-base-400 hover:text-blue-300 transition-colors">
          EDIT
        </button>
        <button onClick={onDelete} className="label-mono text-base-600 hover:text-red-400 transition-colors ml-auto">
          DELETE
        </button>
      </div>

      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
        {server.agents.length === 0 ? (
          <span className="label-mono text-base-600">NO AGENTS ASSIGNED</span>
        ) : (
          server.agents.map((agent) => {
            const info = SUBAGENTS.find((a) => agentKey(a.name) === agent);
            return (
              <span
                key={agent}
                data-phase={info?.phase}
                className="phase-code"
                title={info?.desc ?? agent}
              >
                {info?.name ?? agent}
              </span>
            );
          })
        )}
        {server.env_keys.length + server.header_keys.length > 0 && (
          <span className="label-mono text-base-600 ml-auto">
            {[...server.header_keys, ...server.env_keys].join(" · ")}
          </span>
        )}
      </div>

      <p className="font-mono text-[10.5px] text-base-600 mt-1.5 truncate">
        {server.transport === "stdio"
          ? [server.command, ...server.args].join(" ")
          : server.url}
      </p>

      {status?.error && (
        <p className="font-mono text-[10.5px] text-red-400/90 mt-1 break-words">{status.error}</p>
      )}
      {status?.ok && status.tools.length > 0 && (
        <p className="font-mono text-[10.5px] text-base-500 mt-1 truncate" title={status.tools.join(", ")}>
          {status.tools.length} tool{status.tools.length === 1 ? "" : "s"} · {status.tools.join(", ")}
        </p>
      )}
      {testResult && (
        <p
          className={
            "font-mono text-[10.5px] mt-1 break-words " +
            (testResult.ok ? "text-blue-300" : "text-red-400/90")
          }
        >
          {testResult.ok
            ? `OK ${testResult.latency_ms ?? "?"}ms · ${testResult.tools.join(", ") || "no tools"}`
            : testResult.error}
        </p>
      )}
    </div>
  );
}

export default function McpPanel({ active }: Props) {
  const [data, setData] = useState<McpServersResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [startingOAuth, setStartingOAuth] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, McpTestResponse>>({});

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.listMcpServers());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (active) refresh();
  }, [active, refresh]);

  useEffect(() => {
    if (!connectingId) return;
    let stopped = false;
    const timer = window.setInterval(async () => {
      try {
        const result = await api.mcpOAuthStatus(connectingId);
        if (stopped || result.pending) return;
        setConnectingId(null);
        await refresh();
        if (result.error) setError(result.error);
        else if (!result.complete) setError("OAuth sign-in was interrupted. Click CONNECT to try again.");
      } catch (e) {
        if (stopped) return;
        setConnectingId(null);
        setError(e instanceof Error ? e.message : String(e));
      }
    }, 1500);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [connectingId, refresh]);

  const connect = async (server: McpServerOut) => {
    const popup = window.open("about:blank", "_blank", "width=600,height=750");
    if (!popup) { setError("Allow popups to sign in with OAuth, then try again."); return; }
    popup.opener = null;
    setStartingOAuth(true);
    setError(null);
    try {
      const result = await api.connectMcpOAuth(server.id);
      if (result.error) throw new Error(result.error);
      if (result.authorization_url) {
        popup.location.replace(result.authorization_url);
        setConnectingId(server.id);
      } else {
        popup.close();
        await refresh();
      }
    } catch (e) {
      popup.close();
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setStartingOAuth(false);
    }
  };

  const statusById = useMemo(() => {
    const map: Record<string, McpServerStatus> = {};
    for (const entry of data?.status ?? []) map[entry.server_id] = entry;
    return map;
  }, [data]);

  const patch = (fields: Partial<FormState>) =>
    setForm((prev) => (prev ? { ...prev, ...fields } : prev));

  const startEdit = (server: McpServerOut) =>
    setForm({
      id: server.id,
      name: server.name,
      transport: server.transport,
      enabled: server.enabled,
      command: server.command,
      args: server.args.join(" "),
      url: server.url,
      credentials: "",
      hint: server.credential_hint,
      existingKeys: [...server.header_keys, ...server.env_keys, ...(server.oauth_connected ? ["OAuth"] : [])],
      agents: server.agents,
    });

  const save = async () => {
    if (!form) return;
    setSaving(true);
    setError(null);
    try {
      const creds = parseCredentials(form.credentials);
      const base = {
        name: form.name.trim(),
        transport: form.transport,
        enabled: form.enabled,
        command: form.transport === "stdio" ? form.command.trim() : "",
        args: form.transport === "stdio" ? form.args.split(/\s+/).filter(Boolean) : [],
        url: form.transport === "http" ? form.url.trim() : "",
        agents: form.agents,
      };
      if (form.id) {
        // Only send changed credentials; an empty box keeps saved values.
        const update: Record<string, unknown> = { ...base };
        if (Object.keys(creds).length > 0) {
          update[form.transport === "stdio" ? "env" : "headers"] = creds;
        }
        await api.updateMcpServer(form.id, update);
      } else {
        await api.createMcpServer({
          ...base,
          env: form.transport === "stdio" ? creds : {},
          headers: form.transport === "http" ? creds : {},
        });
      }
      setForm(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  /** Wipe every stored credential for the server being edited. */
  const clearKeys = async () => {
    if (!form?.id) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateMcpServer(form.id, { clear_credentials: true });
      setForm({ ...form, existingKeys: [], credentials: "" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (server: McpServerOut) => {
    setError(null);
    try {
      await api.deleteMcpServer(server.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const toggle = async (server: McpServerOut) => {
    try {
      await api.updateMcpServer(server.id, { enabled: !server.enabled });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const test = async (server: McpServerOut) => {
    setTestingId(server.id);
    try {
      const result = await api.testMcpServer(server.id);
      setTestResults((prev) => ({ ...prev, [server.id]: result }));
    } catch (e) {
      setTestResults((prev) => ({
        ...prev,
        [server.id]: {
          ok: false,
          tools: [],
          error: e instanceof Error ? e.message : String(e),
          latency_ms: null,
        },
      }));
    } finally {
      setTestingId(null);
    }
  };

  const restore = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.restoreMcpPresets();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const servers = data?.servers ?? [];

  return (
    <div className="flex-grow flex flex-col min-h-0 bg-base-900/10">
      <div className="flex-shrink-0 px-5 pt-4 pb-3 border-b border-base-700 bg-base-950/20">
        <h3 className="label-mono text-base-300">MCP CONNECTIONS</h3>
        <p className="font-display text-[12px] text-base-500 italic mt-1.5 leading-snug">
          External tool servers the specialists can call. Assigned tools load on
          connect and are cached per agent; a server that fails degrades to no
          tools instead of breaking a run.
        </p>
        <button
          onClick={() => setForm({ ...EMPTY_FORM })}
          className="mt-3 w-full px-3 py-1.5 label-mono text-base-300 border border-base-600 hover:border-blue-400/60 hover:text-blue-300 bg-base-800/40 transition-colors tick-corners"
        >
          + ADD SERVER
        </button>
        <button
          onClick={restore}
          disabled={saving}
          title="Re-add catalog servers you deleted; existing entries are untouched"
          className="mt-1.5 w-full label-mono text-base-600 hover:text-base-300 transition-colors disabled:opacity-40"
        >
          RESTORE CATALOG
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-2">
        {data && !data.adapter_available && (
          <p className="label-mono text-amber-400/90 leading-relaxed border border-amber-500/30 bg-amber-500/5 px-2.5 py-2">
            MCP ADAPTER MISSING · {data.adapter_error ?? "langchain-mcp-adapters not installed"}
          </p>
        )}
        {error && <p className="font-mono text-[11px] text-red-400/90 break-words">{error}</p>}
        {connectingId && (
          <button className="label-mono text-base-400 hover:text-base-200" onClick={async () => {
            try {
              await api.cancelMcpOAuth(connectingId);
              setConnectingId(null);
              await refresh();
            } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
          }}>CANCEL SIGN-IN</button>
        )}
        {loading && servers.length === 0 && (
          <div className="flex items-center justify-center py-10 gap-3">
            <div className="w-4 h-4 border border-blue-400 border-t-transparent rounded-full animate-spin" />
            <span className="label-mono text-base-500">LOADING…</span>
          </div>
        )}
        {!loading && servers.length === 0 && (
          <div className="px-3 py-8 text-center">
            <p className="font-display text-sm text-base-400 italic">No MCP servers configured.</p>
            <p className="label-mono text-base-600 mt-2">ADD ONE ABOVE</p>
          </div>
        )}

        {servers.map((server) => (
          <ServerRow
            key={server.id}
            server={server}
            status={statusById[server.id]}
            testResult={testResults[server.id]}
            testing={testingId === server.id}
            onTest={() => test(server)}
            onEdit={() => startEdit(server)}
            onDelete={() => remove(server)}
            onToggle={() => toggle(server)}
            onConnect={() => connect(server)}
            connecting={startingOAuth || connectingId !== null}
          />
        ))}

        {form && (
          <div className="border border-base-600 bg-base-900/40 px-3 py-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="label-mono text-base-300">{form.id ? "EDIT SERVER" : "NEW SERVER"}</span>
              <button
                onClick={() => setForm(null)}
                className="ml-auto label-mono text-base-600 hover:text-base-300 transition-colors"
              >
                CANCEL
              </button>
            </div>

            <input
              value={form.name}
              onChange={(e) => patch({ name: e.target.value })}
              placeholder="name (e.g. github)"
              aria-label="Server name"
              className="w-full bg-base-950/60 border border-base-700 focus:border-blue-400/60 outline-none px-2 py-1.5 text-[12px] text-base-200 font-mono"
            />

            <div className="flex gap-2">
              {(["http", "stdio"] as McpTransport[]).map((transport) => (
                <button
                  key={transport}
                  onClick={() => patch({ transport })}
                  className={
                    "flex-1 px-2 py-1 label-mono border transition-colors " +
                    (form.transport === transport
                      ? "border-blue-400/60 text-blue-300 bg-blue-400/10"
                      : "border-base-700 text-base-500 hover:text-base-300")
                  }
                >
                  {transport.toUpperCase()}
                </button>
              ))}
            </div>

            {form.transport === "stdio" ? (
              <>
                <input
                  value={form.command}
                  onChange={(e) => patch({ command: e.target.value })}
                  placeholder="command (uvx / python / node)"
                  aria-label="Command"
                  className="w-full bg-base-950/60 border border-base-700 focus:border-blue-400/60 outline-none px-2 py-1.5 text-[12px] text-base-200 font-mono"
                />
                <input
                  value={form.args}
                  onChange={(e) => patch({ args: e.target.value })}
                  placeholder="arguments, space separated"
                  aria-label="Arguments"
                  className="w-full bg-base-950/60 border border-base-700 focus:border-blue-400/60 outline-none px-2 py-1.5 text-[12px] text-base-200 font-mono"
                />
              </>
            ) : (
              <input
                value={form.url}
                onChange={(e) => patch({ url: e.target.value })}
                placeholder="https://server.example/mcp"
                aria-label="Server URL"
                className="w-full bg-base-950/60 border border-base-700 focus:border-blue-400/60 outline-none px-2 py-1.5 text-[12px] text-base-200 font-mono"
              />
            )}

            <textarea
              value={form.credentials}
              onChange={(e) => patch({ credentials: e.target.value })}
              placeholder={
                form.hint ||
                (form.transport === "stdio"
                  ? "ENV  KEY: value  (one per line)"
                  : "Authorization: Bearer <token>")
              }
              aria-label="Credentials"
              rows={2}
              className="w-full bg-base-950/60 border border-base-700 focus:border-blue-400/60 outline-none px-2 py-1.5 text-[11px] text-base-200 font-mono resize-none"
            />

            {form.existingKeys.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="label-mono text-base-600">SAVED</span>
                {form.existingKeys.map((key) => (
                  <span key={key} className="label-mono text-base-400 border border-base-700 px-1.5 py-0.5">
                    {key} ✓
                  </span>
                ))}
                <button
                  onClick={clearKeys}
                  disabled={saving}
                  className="label-mono text-base-600 hover:text-red-400 transition-colors ml-auto disabled:opacity-40"
                >
                  CLEAR
                </button>
              </div>
            )}

            <p className="font-mono text-[10px] text-base-600 leading-relaxed">
              Values are write-only — the API returns key names, never the tokens.
              {form.id
                ? " Only the keys you type are added or replaced; others stay saved."
                : ""}
            </p>

            <div>
              <span className="label-mono text-base-500">ASSIGN TO AGENTS</span>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {SUBAGENTS.map((agent) => {
                  const key = agentKey(agent.name);
                  const selected = form.agents.includes(key);
                  return (
                    <button
                      key={key}
                      onClick={() =>
                        patch({
                          agents: selected
                            ? form.agents.filter((a) => a !== key)
                            : [...form.agents, key],
                        })
                      }
                      data-phase={agent.phase}
                      className={
                        "phase-code px-1.5 py-0.5 border transition-colors " +
                        (selected ? "border-blue-400/60 bg-blue-400/10" : "border-base-700 opacity-60")
                      }
                      title={agent.desc}
                    >
                      {agent.name}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <label className="flex items-center gap-1.5 label-mono text-base-500">
                <input
                  type="checkbox"
                  checked={form.enabled}
                  onChange={(e) => patch({ enabled: e.target.checked })}
                />
                ENABLED
              </label>
              <button
                onClick={save}
                disabled={saving || !form.name.trim()}
                className="ml-auto label-mono px-3 py-1 border border-blue-400/60 text-blue-300 bg-blue-400/10 hover:bg-blue-400/20 transition-colors disabled:opacity-40"
              >
                {saving ? "SAVING…" : "SAVE"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
