// API client for the SDLC Harness backend
// Backend runs on port 8000 — we call it directly (CORS is enabled).

const API_BASE = "http://localhost:8000";

/** Window event fired on any 401, so AuthGate can re-open the sign-in form. */
export const UNAUTHORIZED_EVENT = "auth:unauthorized";

/**
 * Thrown when the backend rejects the session (missing, expired, revoked).
 *
 * One error type so exactly one place — AuthGate — decides what a dead session
 * means. Without it every call site would have to string-match "401". The
 * constructor also broadcasts the event, because a session can expire between
 * page load and the next poll, and no caller knows to check.
 */
export class UnauthorizedError extends Error {
  constructor(readonly path: string) {
    super(`Unauthorized: ${path}`);
    this.name = "UnauthorizedError";
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
  }
}

// Sessions are an HttpOnly cookie, so every request must opt into sending it.
// Same-site (localhost:3000 -> localhost:8000) means the browser accepts it
// without a CORS preflight dance, but credentials still need to be requested.
const WITH_COOKIE: RequestInit = { credentials: "include" };

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { ...WITH_COOKIE, ...init });
  if (res.status === 401) throw new UnauthorizedError(path);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  // 204 (logout) has no body; res.json() would throw on the empty stream.
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  health: () => fetchApi<import("./types").HealthStatus>("/health"),
  tracing: () => fetchApi<import("./types").TracingStatus>("/tracing"),

  createProject: (projectId: string, threadId: string) =>
    fetchApi<import("./types").ProjectInfo>(
      `/projects?thread_id=${encodeURIComponent(threadId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId }),
      }
    ),

  listArtifacts: (projectId: string, threadId: string) =>
    fetchApi<{ project_id: string; artifacts: import("./agents").ArtifactInfo[] }>(
      `/projects/${projectId}/artifacts?thread_id=${encodeURIComponent(threadId)}`
    ),

  getArtifactContent: (projectId: string, threadId: string, artifactName: string) =>
    fetchApi<import("./types").ArtifactContent>(
      `/projects/${projectId}/artifacts/${artifactName}?thread_id=${encodeURIComponent(threadId)}`
    ),

  uploadFiles: async (projectId: string, threadId: string, files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    const url = `${API_BASE}/upload/${projectId}?thread_id=${encodeURIComponent(threadId)}`;
    const res = await fetch(url, { ...WITH_COOKIE, method: "POST", body: fd });
    if (res.status === 401) throw new UnauthorizedError(url);
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json() as Promise<{
      thread_id: string;
      project_id: string;
      files: { path: string; original_name: string }[];
    }>;
  },

  listUploads: (projectId: string, threadId: string) =>
    fetchApi<{ project_id: string; thread_id: string; files: string[] }>(
      `/upload/${projectId}?thread_id=${encodeURIComponent(threadId)}`
    ),

  getHistory: (threadId: string) =>
    fetchApi<{
      thread_id: string;
      messages: { role: string; content: string }[];
    }>(`/history/${threadId}`),

  deleteSession: (threadId: string) =>
    fetchApi<{ status: string; detail: string }>(`/session/${threadId}`, {
      method: "DELETE",
    }),

  // ── Tool registry ─────────────────────────────────────────────────
  getToolRegistry: () =>
    fetchApi<import("./types").ToolRegistryResponse>("/tools/registry"),

  // ── Custom agents ────────────────────────────────────────────────
  listCustomAgents: () =>
    fetchApi<{ agents: import("./types").CustomAgent[] }>("/agents/custom"),

  createCustomAgent: (body: import("./types").CustomAgentCreate) =>
    fetchApi<import("./types").CustomAgent>("/agents/custom", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  updateCustomAgent: (id: string, body: import("./types").CustomAgentUpdate) =>
    fetchApi<import("./types").CustomAgent>(`/agents/custom/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  deleteCustomAgent: (id: string) =>
    fetchApi<{ status: string; detail: string }>(`/agents/custom/${id}`, {
      method: "DELETE",
    }),

  // ── Model settings (base URL / API key / model names) ────────────
  getModelSettings: () =>
    fetchApi<import("./types").ModelSettingsResponse>("/settings/model"),

  updateModelSettings: (body: import("./types").ModelSettingsUpdate) =>
    fetchApi<import("./types").ModelSettingsResponse>("/settings/model", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  // ── Workspace file explorer ──────────────────────────────────────
  listProjectFiles: (projectId: string, threadId: string, path: string = "") =>
    fetchApi<import("./types").ProjectFileListResponse>(
      `/projects/${projectId}/files?` +
        `path=${encodeURIComponent(path)}` +
        `&thread_id=${encodeURIComponent(threadId)}`
    ),

  // ── Download URL builder ─────────────────────────────────────────
  // Returns a plain URL the browser can hit via <a href> or
  // window.open(); the backend sets Content-Disposition: attachment so
  // the browser saves the response.  `as: "pdf"` lets markdown sources
  // opt into server-side PDF rendering.
  downloadUrl: (
    projectId: string,
    threadId: string,
    path: string,
    as?: "pdf"
  ) =>
    `${API_BASE}/projects/${projectId}/download?` +
      `path=${encodeURIComponent(path)}` +
      `&thread_id=${encodeURIComponent(threadId)}` +
      (as ? `&as=${as}` : ""),

  // ── Conversations + messages (Postgres-backed) ───────────────────
  // Replaces the old localStorage flow. Conversations carry the same
  // id used by the LangGraph thread + Docker container, so a single
  // uuid identifies a chat across every layer.
  listConversations: () =>
    fetchApi<{ conversations: import("./types").ConversationSummary[] }>(
      "/conversations"
    ),

  createConversation: (body: import("./types").ConversationCreate) =>
    fetchApi<import("./types").ConversationSummary>("/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  patchConversation: (id: string, body: { title?: string }) =>
    fetchApi<import("./types").ConversationSummary>(`/conversations/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  deleteConversationRow: (id: string) =>
    fetchApi<{ status: string; detail: string }>(`/conversations/${id}`, {
      method: "DELETE",
    }),

  listMessages: (conversationId: string) =>
    fetchApi<{ conversation_id: string; messages: import("./types").StoredMessage[] }>(
      `/conversations/${conversationId}/messages`
    ),

  appendMessage: (
    conversationId: string,
    body: import("./types").MessageAppend
  ) =>
    fetchApi<import("./types").StoredMessage>(
      `/conversations/${conversationId}/messages`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    ),

  replaceMessages: (
    conversationId: string,
    messages: import("./types").MessageAppend[]
  ) =>
    fetchApi<{ status: string; detail: string }>(
      `/conversations/${conversationId}/messages`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages }),
      }
    ),

  compactConversation: (conversationId: string) =>
    fetchApi<{ message: string; summary: string }>(
      `/conversations/${conversationId}/compact`,
      {
        method: "POST",
      }
    ),

  // ── Conversation export ───────────────────────────────────────────
  // Returns a plain URL the browser can hit via <a href> or
  // window.open(); the backend renders the whole thread (messages, tool
  // calls with input+output, agent reasoning) as Markdown and sets
  // Content-Disposition: attachment so the browser saves the .md file.
  exportConversationUrl: (conversationId: string) =>
    `${API_BASE}/conversations/${conversationId}/export`,

  abortChat: (threadId: string) =>
    fetchApi<{ status: string; detail: string }>("/chat/abort", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: threadId }),
    }),

  // ── Skills management ─────────────────────────────────────────────
  listSkills: () =>
    fetchApi<import("./types").SkillInfo[]>("/skills"),

  getSkillDetails: (skillName: string) =>
    fetchApi<import("./types").SkillDetailsResponse>(`/skills/${encodeURIComponent(skillName)}`),

  updateSkillDetails: (skillName: string, skillContent?: string, learnedContent?: string) =>
    fetchApi<import("./types").SkillDetailsResponse>(
      `/skills/${encodeURIComponent(skillName)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          skill_content: skillContent !== undefined ? skillContent : null,
          learned_content: learnedContent !== undefined ? learnedContent : null,
        }),
      }
    ),
  // ── MCP servers ──────────────────────────────────────────────────────
  connectMcpOAuth: (id: string) =>
    fetchApi<import("./types").McpOAuthStatus>(`/mcp/servers/${id}/oauth`, { method: "POST" }),

  mcpOAuthStatus: (id: string) =>
    fetchApi<import("./types").McpOAuthStatus>(`/mcp/servers/${id}/oauth`),

  cancelMcpOAuth: (id: string) =>
    fetchApi<{ cancelled: boolean }>(`/mcp/servers/${id}/oauth/cancel`, { method: "POST" }),

  listMcpServers: () => fetchApi<import("./types").McpServersResponse>("/mcp/servers"),

  createMcpServer: (body: import("./types").McpServerCreate) =>
    fetchApi<import("./types").McpServerOut>("/mcp/servers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  updateMcpServer: (id: string, body: import("./types").McpServerUpdate) =>
    fetchApi<import("./types").McpServerOut>(`/mcp/servers/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  deleteMcpServer: (id: string) =>
    fetchApi<{ deleted: boolean }>(`/mcp/servers/${id}`, { method: "DELETE" }),

  testMcpServer: (id: string) =>
    fetchApi<import("./types").McpTestResponse>(`/mcp/servers/${id}/test`, { method: "POST" }),

  /** Re-add catalog entries that were deleted; existing servers untouched. */
  restoreMcpPresets: () =>
    fetchApi<import("./types").McpServerOut[]>("/mcp/servers/presets", { method: "POST" }),
};

export { API_BASE };
