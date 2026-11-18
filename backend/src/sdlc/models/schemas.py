"""Pydantic models for the API request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """A single chat message from the user."""

    message: str = Field(..., description="The user's message, may include @mention")
    thread_id: str = Field(default="default", description="Conversation thread ID")
    project_id: str = Field(default="default", description="Project workspace ID")
    uploaded_files: list[str] = Field(
        default_factory=list,
        description="Paths of files already uploaded (inside the container)",
    )
    file_names: list[str | None] = Field(
        default_factory=list,
        description="Original filenames corresponding to uploaded_files (human-readable)",
    )


class ChatAbortRequest(BaseModel):
    """Request to abort/cancel an in-flight chat run on a thread."""

    thread_id: str = Field(..., description="The thread ID of the active run to cancel")


class ChatResponse(BaseModel):
    """The agent's response."""

    message: str = Field(..., description="The agent's text response")
    thread_id: str = Field(..., description="Conversation thread ID")
    project_id: str = Field(..., description="Project workspace ID")


class UploadResponse(BaseModel):
    """Response after uploading one or more files."""

    thread_id: str
    project_id: str = "default"
    files: list[dict[str, str]] = Field(
        default_factory=list,
        description="[{path, original_name}] for each uploaded file",
    )


class ProjectCreateRequest(BaseModel):
    """Request to create a new project workspace."""

    project_id: str = Field(
        default="default",
        description="Project ID (used as workspace directory name)",
    )


class ProjectCreateResponse(BaseModel):
    """Response after creating a project workspace."""

    project_id: str
    root: str = Field(..., description="Container-absolute path to project root")
    status: str = "created"


class ArtifactListResponse(BaseModel):
    """Response listing artifacts in a project."""

    project_id: str
    artifacts: list[dict[str, str]] = Field(
        default_factory=list,
        description="[{name, phase, status, agent}] for each expected artifact. "
                    "`name` is the phase-qualified path (e.g. 'requirements/REQUIREMENTS.md'); "
                    "`phase` is one of sources/requirements/design/planning/diagrams.",
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    container_id: str | None = None
    container_running: bool = False


class TracingStatusResponse(BaseModel):
    """LangSmith tracing status response."""

    enabled: bool = False
    project: str = ""
    endpoint: str = ""
    status: str = "disabled"
    api_key_set: bool = False


# ── Custom (user-created) agents ────────────────────────────────────────


class CustomAgent(BaseModel):
    """A user-created subagent stored in custom_agents.json."""

    id: str
    name: str
    description: str
    system_prompt: str
    tools: list[str] = Field(
        default_factory=list,
        description="Tool category keys this agent can use (e.g. ['diagram', 'api'])",
    )
    created_at: str
    updated_at: str


class CustomAgentCreate(BaseModel):
    """Request body for creating a new custom agent."""

    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1, max_length=2000)
    system_prompt: str = Field(..., min_length=1, max_length=50000)
    tools: list[str] = Field(
        default_factory=list,
        description="Tool category keys this agent can use (e.g. ['diagram', 'api'])",
    )


class CustomAgentUpdate(BaseModel):
    """Request body for updating an existing custom agent. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    system_prompt: str | None = Field(default=None, min_length=1, max_length=50000)
    tools: list[str] | None = Field(
        default=None,
        description="Tool category keys this agent can use (e.g. ['diagram', 'api'])",
    )


class CustomAgentListResponse(BaseModel):
    """List of all custom agents."""

    agents: list[CustomAgent]


class ToolRegistryEntry(BaseModel):
    """A single entry in the tool registry."""

    label: str
    description: str
    tools: list[str]
    available: bool


class ToolRegistryResponse(BaseModel):
    """Full tool registry with availability status."""

    categories: dict[str, ToolRegistryEntry]




class ModelSettings(BaseModel):
    """Resolved model settings (stored override > env/default cascade).

    The API key is intentionally NOT part of this model — it is never
    returned to the client. The response carries an ``api_key_set`` flag
    instead.
    """

    model_provider: str
    reasoning_effort: str
    base_url: str
    agent_model: str
    vision_model: str
    retry_model: str


class ModelSettingsResponse(BaseModel):
    """GET /settings/model — effective (non-secret) values, whether an API
    key is configured, and which fields are explicitly stored. The
    ``stored`` map masks the API key value so it is never leaked."""

    effective: ModelSettings
    api_key_set: bool
    stored: dict[str, str]


class ModelSettingsUpdate(BaseModel):
    """PUT /settings/model — any subset of the five keys. Empty string
    clears an override (the field falls back to env or default). Omit
    ``api_key`` to leave the stored key untouched; send "" to clear it."""

    model_provider: str | None = Field(default=None, max_length=100)
    reasoning_effort: str | None = Field(default=None, max_length=50)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=500)
    agent_model: str | None = Field(default=None, max_length=200)
    vision_model: str | None = Field(default=None, max_length=200)
    retry_model: str | None = Field(default=None, max_length=200)




# ── Conversations + messages (Postgres-backed replacement for localStorage) ──


class ConversationBase(BaseModel):
    """Common fields shared by every conversation response shape."""

    id: str = Field(..., description="Client-generated id; also the LangGraph thread id.")
    title: str = ""
    project_id: str = "default"
    created_at: str = Field(..., description="ISO 8601 UTC timestamp.")
    updated_at: str = Field(..., description="ISO 8601 UTC timestamp.")


class ConversationSummary(ConversationBase):
    """List-view payload — includes message_count for sidebar badges."""

    message_count: int = 0


class ConversationCreate(BaseModel):
    """Create a new conversation row.

    The client passes its own id (so the LangGraph thread_id, Docker
    container name, and DB row all share the same identifier from turn
    zero). All other fields are optional and default server-side.
    """

    id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(default="", max_length=200)
    project_id: str = Field(default="default", max_length=64)


class ConversationUpdate(BaseModel):
    """Patch fields on an existing conversation. Title-only for now."""

    title: str | None = Field(default=None, max_length=200)


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class MessageAttachment(BaseModel):
    """A file the user pinned to a message (rendered as a chip)."""

    name: str
    path: str


class MessageToolCall(BaseModel):
    """Tool-call payload preserved from the SSE stream."""

    toolId: str = ""
    toolName: str = ""
    toolArgs: str = ""
    result: str | None = None
    isRunning: bool | None = None


class MessageCreate(BaseModel):
    """Append a message to a conversation.

    Mirrors the frontend's ChatMessageType. ``content`` is plain text;
    ``tool_calls`` / ``attachments`` are the rich JSONB sidecars.
    """

    role: str = Field(..., description='"human" | "ai" | "system"')
    content: str = ""
    agent_name: str | None = None
    trace_url: str | None = None
    tool_calls: list[MessageToolCall] | None = None
    attachments: list[MessageAttachment] | None = None
    reasoning: str | None = None


class MessageOut(BaseModel):
    """A single message returned to the frontend."""

    id: int
    conversation_id: str
    role: str
    content: str
    agent_name: str | None = None
    trace_url: str | None = None
    tool_calls: list[dict] | None = None
    attachments: list[dict] | None = None
    reasoning: str | None = None
    created_at: str


class MessageListResponse(BaseModel):
    conversation_id: str
    messages: list[MessageOut]


# ── Skills management ────────────────────────────────────────────────────

class SkillInfo(BaseModel):
    name: str
    has_skill: bool
    has_learned: bool


class SkillDetailsResponse(BaseModel):
    name: str
    skill_content: str
    learned_content: str


class SkillUpdateRequest(BaseModel):
    skill_content: str | None = None
    learned_content: str | None = None

# ── MCP servers ──────────────────────────────────────────────────────────
# Credential-bearing maps (env / headers) are write-only: responses expose the
# key names and never the values. See services/mcp_settings.py.

class McpServerOut(BaseModel):
    """One stored MCP server as returned to the client (secrets masked)."""

    id: str
    name: str
    description: str = ""
    credential_hint: str = ""
    transport: str
    enabled: bool
    command: str = ""
    args: list[str] = Field(default_factory=list)
    url: str = ""
    agents: list[str] = Field(default_factory=list)
    env_keys: list[str] = Field(default_factory=list)
    header_keys: list[str] = Field(default_factory=list)
    oauth_connected: bool = False


class McpServerCreate(BaseModel):
    """POST /mcp/servers — a new server definition."""

    name: str
    description: str = ""
    credential_hint: str = ""
    transport: str = Field(default="stdio", description="'stdio' or 'http'")
    enabled: bool = True
    command: str = ""
    args: list[str] = Field(default_factory=list)
    url: str = ""
    env: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    agents: list[str] = Field(default_factory=list)


class McpServerUpdate(BaseModel):
    """PUT /mcp/servers/{id} — any subset.

    Credential maps merge at key level: sending {"Authorization": "<new token>"}
    upserts that header and leaves every other stored header alone, so editing a
    description cannot wipe a saved API key. Set clear_credentials to wipe them
    all on purpose.
    """

    name: str | None = None
    description: str | None = None
    credential_hint: str | None = None
    transport: str | None = None
    enabled: bool | None = None
    command: str | None = None
    args: list[str] | None = None
    url: str | None = None
    env: dict[str, str] | None = None
    headers: dict[str, str] | None = None
    agents: list[str] | None = None
    clear_credentials: bool = False


class McpServerStatus(BaseModel):
    """Last load attempt for a server: tools it exposed, or why it failed."""

    server_id: str
    name: str
    ok: bool
    tools: list[str] = Field(default_factory=list)
    error: str | None = None
    checked_at: float | None = None
    latency_ms: int | None = None


class McpServersResponse(BaseModel):
    """GET /mcp/servers."""

    servers: list[McpServerOut]
    adapter_available: bool
    adapter_error: str | None = None
    status: list[McpServerStatus] = Field(default_factory=list)


class McpTestResponse(BaseModel):
    """POST /mcp/servers/{id}/test."""

    ok: bool
    tools: list[str] = Field(default_factory=list)
    error: str | None = None
    latency_ms: int | None = None


# ── Auth (accounts + sessions) ─────────────────────────────────────────


class RegisterRequest(BaseModel):
    """POST /auth/register. Open signup — no invite, no admin."""

    email: str = Field(..., max_length=320)
    password: str = Field(..., max_length=512)
    display_name: str = Field(default="", max_length=120)


class LoginRequest(BaseModel):
    """POST /auth/login."""

    email: str = Field(..., max_length=320)
    password: str = Field(..., max_length=512)


class ChangePasswordRequest(BaseModel):
    """POST /auth/password. Current password proves it is the owner, not a
    borrowed cookie."""

    current_password: str = Field(..., max_length=512)
    new_password: str = Field(..., max_length=512)


class AuthUser(BaseModel):
    """The signed-in identity, as the frontend needs it. Never the hash."""

    id: int
    email: str
    display_name: str = ""

