// Types for the SDLC Harness frontend

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  agentName?: string;
  traceUrl?: string;
  timestamp: number;
  /** Tool calls collected during streaming */
  toolCalls?: ToolCallInfo[];
  /** Files the user attached to this message (rendered as chips in the bubble) */
  attachments?: Array<{ name: string; path: string }>;
  reasoning?: string;
}

export interface ToolCallInfo {
  toolId: string;
  toolName: string;
  toolArgs: string;
  result?: string;
  isRunning?: boolean;
}

export interface Conversation {
  id: string;           // threadId
  title: string;        // auto-generated from first user message
  createdAt: number;    // timestamp
  updatedAt: number;    // timestamp
  projectId: string;
  messageCount: number;
}

export interface ProjectInfo {
  project_id: string;
  root: string;
  status: string;
}

export interface TracingStatus {
  enabled: boolean;
  project: string;
  endpoint: string;
  status: string;
  api_key_set: boolean;
}

export interface HealthStatus {
  status: string;
  container_id: string | null;
  container_running: boolean;
}

export interface UploadedFile {
  path: string;
  originalName: string;
}

/** A file the user has attached to the chat composer.
 *  - "pending"  — selected, upload in flight; render with a spinner.
 *  - "ready"    — upload finished; included in the next /chat/stream send.
 *  - "error"    — upload failed; user can dismiss; not sent.
 */
export type LocalUpload =
  | { kind: "pending"; localId: string; name: string; size: number }
  | {
      kind: "ready";
      localId: string;
      path: string;
      original_name: string;
      size: number;
    }
  | { kind: "error"; localId: string; name: string; message: string };

/** A single todo item (mirrors TodoList's TodoItem; structural). */
export interface TodoItemInfo {
  content: string;
  status: "pending" | "in_progress" | "completed" | "failed";
}

export interface SubagentInfo {
  name: string;
  path: string[];
  status: "started" | "completed" | "failed";
  messages: Array<{ role: "assistant"; content: string; reasoning?: string }>;
  toolCalls: ToolCallInfo[];
  /** The task instruction the orchestrator delegated to this subagent. */
  task?: string;
  /** This subagent's own write_todos checklist. */
  todos?: TodoItemInfo[];
  /** Timestamp when this subagent was first detected. */
  startedAt?: number;
  /** Timestamp when this subagent completed or failed. */
  completedAt?: number;
}

/** One entry in the Thinking tab — native model reasoning or derived planning. */
export interface ReasoningEntry {
  agent: string;        // "" = orchestrator
  content: string;
  source: "model" | "planning";
  ts: number;
}

export interface SSEEvent {
  type: "token" | "done" | "error" | "tool_call" | "tool_args" | "tool_result" | "values" | "subagent_started" | "subagent_completed" | "subagent_failed" | "approval_requested" | "auto_approved" | "reasoning" | "todos" | "run_started";
  /**
   * Whether this run resumed work already in the transcript (run_started).
   *
   * A resumed run re-emits the interrupted work with fresh message ids, so the
   * client cannot tell a replay from new output by `_seq` (which restarts at 1
   * each run). The backend marks it here.
   */
  resume?: boolean;
  /** How many prior messages/tool calls this run replays (run_started). */
  replayed?: number;
  content?: string;
  /** Delegated task instruction (subagent_started events). */
  task?: string;
  /** Todo items (todos events). */
  items?: Array<{ content: string; status: "pending" | "in_progress" | "completed" | "failed" }>;
  /** Reasoning origin (reasoning events): native model output vs derived planning. */
  source?: "model" | "planning";
  detail?: string;
  trace_url?: string;
  tool_name?: string;
  tool_args?: string;
  tool_id?: string;
  /**
   * Monotonic position of this event within its run.
   *
   * The backend replays a run's whole event history to every new
   * subscriber, so a re-attach re-delivers events already applied. This is
   * the only way to tell a replay from new output.
   */
  _seq?: number;
  /** Which subagent this event belongs to (empty = orchestrator). */
  agent?: string;
  /** Subagent namespace path (for started/completed events). */
  path?: string[];
  /** Subagent summaries in the final done event. */
  subagents?: Array<{ name: string; path: string[] }>;
  /** Todo items from state snapshots. */
  todos?: Array<{ content: string; status: "pending" | "in_progress" | "completed" | "failed" }>;
  /** Id of the approval interrupt (approval_requested events). */
  interrupt_id?: string;
  /** The HITL request payload (approval_requested / auto_approved events). */
  request?: HITLRequest;
}

/** One agent action awaiting human review (langchain HITL contract). */
export interface HITLActionRequest {
  name: string;
  args: Record<string, unknown>;
  description?: string;
}

export interface HITLReviewConfig {
  action_name: string;
  allowed_decisions: Array<"approve" | "reject" | "edit" | "respond">;
}

/** Payload carried by an `approval_requested` SSE event. */
export interface HITLRequest {
  action_requests: HITLActionRequest[];
  review_configs: HITLReviewConfig[];
}

/** A pending human-approval interrupt held in page state. */
export interface PendingApproval {
  interruptId: string;
  request: HITLRequest;
  agent?: string;
}

/** One decision sent back to POST /chat/{thread_id}/decision. */
export type HITLDecision =
  | { type: "approve" }
  | { type: "reject"; message?: string }
  | { type: "edit"; edited_action: { name: string; args: Record<string, unknown> } };

export interface ArtifactContent {
  project_id: string;
  name: string;
  content: string;
  language: string;
  size: number;
}

/** A user-created subagent stored on the backend in custom_agents.json. */
export interface CustomAgent {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  tools: string[];
  created_at: string;
  updated_at: string;
}

export interface CustomAgentCreate {
  name: string;
  description: string;
  system_prompt: string;
  tools?: string[];
}

export type CustomAgentUpdate = Partial<CustomAgentCreate>;

/** A single entry in the tool registry (returned by GET /tools/registry). */
export interface ToolRegistryEntry {
  label: string;
  description: string;
  tools: string[];
  available: boolean;
}

export interface ToolRegistryResponse {
  categories: Record<string, ToolRegistryEntry>;
}

/** Resolved model settings. The API key is never returned — `api_key_set`
 *  on the response reports whether one is configured. */
export interface ModelSettings {
  model_provider: string;
  reasoning_effort: string;
  base_url: string;
  agent_model: string;
  vision_model: string;
  retry_model: string;
}

export interface ModelSettingsResponse {
  effective: ModelSettings;
  /** Whether an API key is configured (via override or env). */
  api_key_set: boolean;
  /** Subset explicitly stored — keys here are overrides. API key masked. */
  stored: Record<string, string>;
}

/** Partial update. Include `api_key` only to change it; "" clears it. */
export type ModelSettingsUpdate = Partial<ModelSettings & { api_key: string }>;

/** One entry returned by GET /projects/{id}/files. */
export interface ProjectFileEntry {
  name: string;
  type: "file" | "dir";
  /** Bytes for files, sum of immediate-children apparent size for dirs (find behaviour). */
  size: number;
  /** UNIX epoch seconds. */
  mtime: number;
}

export interface ProjectFileListResponse {
  project_id: string;
  /** Path relative to the project root (empty string = root). */
  path: string;
  entries: ProjectFileEntry[];
}

/** One row from GET /conversations — sidebar list shape. */
export interface ConversationSummary {
  id: string;
  title: string;
  project_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

/** Body for POST /conversations. */
export interface ConversationCreate {
  id: string;
  title?: string;
  project_id?: string;
}

/** Message body persisted to / hydrated from the backend. Mirrors
 *  ChatMessageType but uses the wire-shape role names ("human" | "ai" |
 *  "system") and exposes the JSONB sidecar fields the backend returns. */
export interface StoredMessage {
  id: number;
  conversation_id: string;
  role: string;
  content: string;
  agent_name: string | null;
  trace_url: string | null;
  tool_calls: ToolCallInfo[] | null;
  attachments: Array<{ name: string; path: string }> | null;
  reasoning: string | null;
  created_at: string;
}

/** Body for POST / PUT /conversations/{id}/messages. */
export interface MessageAppend {
  role: string;
  content?: string;
  agent_name?: string | null;
  trace_url?: string | null;
  tool_calls?: ToolCallInfo[] | null;
  attachments?: Array<{ name: string; path: string }> | null;
  reasoning?: string | null;
}

export interface SkillInfo {
  name: string;
  has_skill: boolean;
  has_learned: boolean;
}

export interface SkillDetailsResponse {
  name: string;
  skill_content: string;
  learned_content: string;
}
// ── MCP servers ──────────────────────────────────────────────────────────
// Credential maps are write-only: the API returns key names (env_keys /
// header_keys), never values.

export type McpTransport = "stdio" | "http";

export interface McpServerOut {
  id: string;
  name: string;
  description: string;
  /** Which credential the server expects, e.g. "Authorization: Bearer <PAT>". */
  credential_hint: string;
  transport: McpTransport;
  enabled: boolean;
  command: string;
  args: string[];
  url: string;
  agents: string[];
  env_keys: string[];
  header_keys: string[];
  oauth_connected?: boolean;
}

export interface McpOAuthStatus {
  pending: boolean;
  complete: boolean;
  error: string | null;
  authorization_url?: string | null;
}

export interface McpServerCreate {
  name: string;
  description?: string;
  credential_hint?: string;
  transport: McpTransport;
  enabled: boolean;
  command: string;
  args: string[];
  url: string;
  env: Record<string, string>;
  headers: Record<string, string>;
  agents: string[];
}

/** Credential maps merge per key; clear_credentials wipes them on purpose. */
export type McpServerUpdate = Partial<McpServerCreate> & { clear_credentials?: boolean };

export interface McpServerStatus {
  server_id: string;
  name: string;
  ok: boolean;
  tools: string[];
  error: string | null;
  checked_at: number | null;
  latency_ms: number | null;
}

export interface McpServersResponse {
  servers: McpServerOut[];
  adapter_available: boolean;
  adapter_error: string | null;
  status: McpServerStatus[];
}

export interface McpTestResponse {
  ok: boolean;
  tools: string[];
  error: string | null;
  latency_ms: number | null;
}

