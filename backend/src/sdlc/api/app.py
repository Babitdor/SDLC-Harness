"""FastAPI application — chat, streaming, file-upload, and project endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

# Matches `"subagent_type": "<name>"` inside the streaming JSON args
# of the orchestrator's `task` tool call. Defined once at module level
# rather than re-compiled on every streamed chunk.
SUBAGENT_TYPE_RE = re.compile(r'"subagent_type"\s*:\s*"([^"]+)"')

def _extract_task_field(args_str: str, field: str) -> str:
    """Pull a string field (e.g. ``description``) from buffered task-tool args.

    Prefers a full ``json.loads`` (the args are complete by the time a subagent
    starts); falls back to a tolerant regex when the buffer isn't valid JSON.
    """
    if not args_str:
        return ""
    try:
        obj = json.loads(args_str)
        val = obj.get(field)
        if isinstance(val, str):
            return val
    except (json.JSONDecodeError, AttributeError):
        pass
    m = re.search(rf'"{re.escape(field)}"\s*:\s*"((?:[^"\\]|\\.)*)"', args_str)
    if m:
        try:
            return json.loads(f'"{m.group(1)}"')  # unescape \n, \" etc.
        except json.JSONDecodeError:
            return m.group(1)
    return ""

def _parse_write_todos(args_str: str) -> list[dict] | None:
    """Return the todo list from buffered ``write_todos`` args, or None.

    ``None`` means "not parseable yet" (args still streaming) — callers should
    just keep buffering.
    """
    try:
        obj = json.loads(args_str)
    except (json.JSONDecodeError, TypeError):
        return None
    todos = obj.get("todos") if isinstance(obj, dict) else None
    return todos if isinstance(todos, list) else None

def _extract_native_reasoning(msg_chunk: Any) -> str:
    """Return model-native reasoning text from a message chunk, or ``""``.

    Future-proofs the Thinking tab: surfaces extended-thinking / reasoning when
    a capable model/gateway provides it (currently empty for the Mistral
    gateway). Checks both ``additional_kwargs`` and structured content blocks.
    """
    parts: list[str] = []
    ak = getattr(msg_chunk, "additional_kwargs", None) or {}
    for key in ("reasoning_content", "reasoning"):
        val = ak.get(key)
        if isinstance(val, str) and val:
            parts.append(val)
        elif isinstance(val, dict):  # some gateways nest {"text": "..."}
            text = val.get("text") or val.get("content")
            if isinstance(text, str) and text:
                parts.append(text)
    content = getattr(msg_chunk, "content", None)
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") in ("thinking", "reasoning"):
                text = block.get("thinking") or block.get("text") or block.get("reasoning")
                if isinstance(text, str) and text:
                    parts.append(text)
    return "".join(parts)

# Many open reasoning models (DeepSeek-R1, Qwen-QwQ, nemotron, …) served
# through OpenAI-compatible gateways WITHOUT a reasoning parser emit their
# chain-of-thought inline as ``<think>…</think>`` in the message content
# rather than in ``additional_kwargs.reasoning_content``. Left in the content
# stream it either pollutes the answer or — because the frontend markdown
# renderer drops raw HTML blocks — vanishes entirely. We split it out here so
# it flows to the Thinking section like any other native reasoning.
_THINK_OPEN = "<think>"
_THINK_CLOSE = "</think>"

def _partial_suffix_len(s: str, tag: str) -> int:
    """Length of the longest suffix of *s* that is a proper prefix of *tag*.

    Lets us hold back a split-across-chunks tag (e.g. a delta ending in
    ``"<thi"``) until the next delta confirms or denies it.
    """
    for k in range(min(len(s), len(tag) - 1), 0, -1):
        if tag.startswith(s[-k:]):
            return k
    return 0

def _split_think(delta: str, state: dict) -> tuple[str, str]:
    """Split a streamed content *delta* into ``(visible, reasoning)``.

    ``state`` (mutable) carries ``in_think`` and a ``buf`` holding a partial
    boundary tag straddling two deltas, so ``<think>`` / ``</think>`` are
    handled even when a provider splits them across chunks.
    """
    buf = state.get("buf", "") + delta
    visible: list[str] = []
    reasoning: list[str] = []
    in_think = state.get("in_think", False)

    while buf:
        if in_think:
            idx = buf.find(_THINK_CLOSE)
            if idx == -1:
                keep = _partial_suffix_len(buf, _THINK_CLOSE)
                reasoning.append(buf[: len(buf) - keep])
                buf = buf[len(buf) - keep:]
                break
            reasoning.append(buf[:idx])
            buf = buf[idx + len(_THINK_CLOSE):]
            in_think = False
        else:
            idx = buf.find(_THINK_OPEN)
            if idx == -1:
                keep = _partial_suffix_len(buf, _THINK_OPEN)
                visible.append(buf[: len(buf) - keep])
                buf = buf[len(buf) - keep:]
                break
            visible.append(buf[:idx])
            buf = buf[idx + len(_THINK_OPEN):]
            in_think = True

    state["in_think"] = in_think
    state["buf"] = buf
    return "".join(visible), "".join(reasoning)

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage, HumanMessage
from sse_starlette.sse import EventSourceResponse

from sdlc.services.agent import (
    close_checkpointer,
    container_name_for,
    create_orchestrator,
    init_checkpointer,
)
from sdlc.sandbox.docker_backend import (
    DockerBackend,
    ensure_image,
    gc_orphan_containers,
)
from sdlc.core.config import (
    ARTIFACT_CACHE_TTL,
    CHECKPOINT_DB_PATH,
    CORS_ORIGINS,
    DOCKER_IMAGE,
    DOCKER_ORPHAN_TTL_HOURS,
    HOST,
    MAX_UPLOAD_SIZE_MB,
    PORT,
    THREAD_POOL_SIZE,
)
from sdlc.services.file_upload import ensure_host_upload_dir, upload_file_to_container
from sdlc.models.schemas import (
    ArtifactListResponse,
    ChatRequest,
    ChatAbortRequest,
    ChatResponse,
    ConversationCreate,
    ConversationListResponse,
    ConversationSummary,
    ConversationUpdate,
    CustomAgent,
    CustomAgentCreate,
    CustomAgentListResponse,
    CustomAgentUpdate,
    ToolRegistryResponse,
    HealthResponse,
    MessageCreate,
    MessageListResponse,
    MessageOut,
    ModelSettings,
    ModelSettingsResponse,
    ModelSettingsUpdate,
    ProjectCreateRequest,
    ProjectCreateResponse,
    TracingStatusResponse,
    UploadResponse,
    SkillInfo,
    SkillDetailsResponse,
    SkillUpdateRequest,
    McpServerOut,
    McpServerCreate,
    McpServerUpdate,
    McpServerStatus,
    McpServersResponse,
    McpTestResponse,
)
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException

from sdlc.api.auth import CurrentUser, _clear_session_cookie, require_user
from sdlc.api.auth import router as auth_router
from sdlc.services import conversations as conversations_store
from sdlc.services import custom_agents as custom_agents_store
from sdlc.services import mcp as mcp_client
from sdlc.services import mcp_settings
from sdlc.services import model_settings
from sdlc.services.caveman import CavemanStats
from sdlc.services.usage import UsageLedger
from sdlc.db import session_scope
from sdlc.core.tracing import (
    is_tracing_enabled,
    make_trace_metadata,
    setup_tracing,
)
from sdlc.services.artifacts import (
    ROOT_ARTIFACTS,
    expected_artifact_paths,
    regenerate_index,
    scan_workspace_files,
)
from sdlc.services.workspace import (
    AGENT_ARTIFACTS,
    ARTIFACT_AGENT,
    DEFAULT_PROJECT_GRAPH,
    ProjectWorkspace,
)
from sdlc.services.document_preview import preview_binary

# Determine frontend directory (repo root/frontend)
_FRONTEND_DIR = Path(__file__).resolve().parents[4] / "frontend"

logger = logging.getLogger(__name__)
logging.getLogger("sdlc").setLevel(logging.INFO)
logger.warning("SDLC logging initialized at INFO level")

# ── Artifact cache ──────────────────────────────────────────────────────
# Caches artifact list results per (project_id, thread_id) with a short
# TTL. The frontend polls every 2s; without this cache, each poll fires 15
# Docker exec calls. With a 1s TTL, we skip ~50% of polls entirely.
# Entry: {key: (timestamp, list_of_artifact_dicts)}
_artifact_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}

# Tracks the last (path, mtime) frozenset signature seen per project:thread.
# When the next poll's stat output produces a different signature, the
# auto-regenerated `index.md` is rewritten. This keeps the cheap polling
# path cheap and only pays the index-write cost on real changes.
_artifact_index_sig: dict[str, frozenset[tuple[str, int]]] = {}

# ── Session registry ────────────────────────────────────────────────────
# Each chat session gets its own Docker container + orchestrator agent.
# Container is created on first message and destroyed when the session is deleted.

_SessionEntry = tuple[Any, DockerBackend]  # (agent, backend)
_sessions: dict[str, _SessionEntry] = {}
_tracing_info: dict = {}
_SANDBOX_WARM_TASK: asyncio.Task[None] | None = None


async def _warm_sandbox() -> None:
    """Pull the sandbox image (if absent) and sweep orphaned containers.

    Both steps are daemon round trips measured in seconds on a cold host, so
    they run once, off the event loop, while the server is already serving.
    Failures are logged inside the helpers and never propagate: a missing
    Docker daemon must surface on the first real chat, not as a boot failure.
    """
    try:
        await asyncio.to_thread(ensure_image, DOCKER_IMAGE)
        await asyncio.to_thread(gc_orphan_containers, DOCKER_ORPHAN_TTL_HOURS)
    except Exception as exc:  # noqa: BLE001 — warm-up is best effort
        logger.warning("Sandbox warm-up failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Startup: initialise tracing, upload dir, and tuning.

    Containers are created per-session.
    """
    global _tracing_info

    # ── Tune the anyio thread pool for I/O-heavy workloads ──────────
    # Default is 40 tokens — far too low when the agent's tools and
    # concurrent artifact reads both use the same pool for Docker exec.
    # Docker exec is I/O-bound (waiting on daemon), so 100 threads is
    # reasonable.  Tunable via THREAD_POOL_SIZE env var.
    import anyio.to_thread

    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = THREAD_POOL_SIZE
    logger.info("AnyIO thread pool: %d tokens", THREAD_POOL_SIZE)

    ensure_host_upload_dir()

    # Open the async SQLite checkpoint connection used by every per-thread
    # agent. Must complete before any /chat/stream call.
    Path(CHECKPOINT_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    await init_checkpointer()

    # Open the Postgres engine and run pending Alembic migrations.
    # `init_db()` calls `engine.dispose()` first to drop any connection
    # pool entries inherited from gunicorn's pre-fork import — otherwise
    # workers deadlock on the first `engine.connect()` and the lifespan
    # never reaches `yield`.
    from sdlc.db import init_db

    await init_db()

    # Re-assert `sdlc` logging AFTER Alembic's fileConfig runs (init_db →
    # migrations). fileConfig uses disable_existing_loggers=True, which DISABLES
    # every sdlc.* logger that already existed at import time (sdlc.api.app,
    # sdlc.services.async_webhook, …) — that's why their INFO/operational logs
    # (webhook injection, auto-resume wake-ups) silently vanished while
    # lazily-imported sdlc.tools.* loggers still showed. Re-enable the whole
    # sdlc.* tree, attach a dedicated stdout handler, and stop propagation so
    # records aren't double-printed via the root handler.
    _sdlc_logger = logging.getLogger("sdlc")
    _sdlc_logger.setLevel(logging.INFO)
    for _name, _lg in logging.Logger.manager.loggerDict.items():
        if (_name == "sdlc" or _name.startswith("sdlc.")) and isinstance(_lg, logging.Logger):
            _lg.disabled = False
    if not any(
        isinstance(h, logging.StreamHandler) for h in _sdlc_logger.handlers
    ):
        _h = logging.StreamHandler()
        _h.setFormatter(logging.Formatter("%(levelname)-5.5s [%(name)s] %(message)s"))
        _sdlc_logger.addHandler(_h)
    _sdlc_logger.propagate = False

    # Fill the MCP tool cache in the background. create_orchestrator() is sync
    # and only reads the cache, and an unreachable MCP server must not delay
    # boot - the same reasoning that moved the tracing check off-loop above.
    global _MCP_WARM_TASK
    _MCP_WARM_TASK = asyncio.create_task(_warm_mcp_tools())

    # Warm the sandbox image and sweep orphaned sandboxes off the boot path.
    # A cold `docker run` on a missing image pays for the whole pull inside the
    # first chat's first message; doing it here (in a worker thread, after
    # yield would be too late) keeps first-message latency flat. Both steps
    # swallow their own errors — Docker being down must not stop the backend.
    global _SANDBOX_WARM_TASK
    _SANDBOX_WARM_TASK = asyncio.create_task(_warm_sandbox())

    # Initialise LangSmith tracing. The connectivity check inside
    # `setup_tracing()` is synchronous (langsmith Client.list_runs has no
    # configurable timeout) — running it inline on the lifespan event
    # loop hung startup forever when LangSmith was slow or under load,
    # which manifested as the backend appearing "healthy" while every
    # endpoint that needed the checkpointer 500'd because lifespan never
    # reached `yield`. Off-loop with a strict timeout so a flaky external
    # never blocks boot.
    try:
        _tracing_info = await asyncio.wait_for(
            asyncio.to_thread(setup_tracing), timeout=5.0
        )
    except asyncio.TimeoutError:
        _tracing_info = {
            "tracing_enabled": False,
            "status": "timeout",
            "project": "",
            "endpoint": "",
            "api_key_set": False,
        }
        logger.warning("LangSmith connectivity check timed out — continuing without tracing status")
    if _tracing_info.get("tracing_enabled"):
        logger.info(
            "LangSmith tracing: project=%s status=%s",
            _tracing_info.get("project"),
            _tracing_info.get("status"),
        )
    else:
        logger.info("LangSmith tracing: disabled")

    logger.info("Server ready — Docker containers created per-session on first chat")

    yield

    # On shutdown, stop containers but keep them on disk so workspace data
    # and (if the chat still exists in the frontend) the container survive
    # the restart. Containers are only removed when a chat is explicitly
    # deleted via DELETE /session/{thread_id}.
    for thread_id in list(_sessions.keys()):
        _stop_session_keep_container(thread_id)
    logger.info("All session containers stopped (kept on disk)")

    # Close the async checkpoint DB connection cleanly.
    await close_checkpointer()

    # Dispose the Postgres engine.
    from sdlc.db import close_db

    await close_db()

app = FastAPI(
    title="SDLC Agent Orchestrator",
    version="0.2.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────
# Explicit origins, never "*": a browser refuses to attach a cookie to a
# wildcard origin, so that combination does not fail open — it fails as
# "login quietly doesn't stick", which is far harder to diagnose.
if "*" in CORS_ORIGINS:
    logger.warning(
        "CORS_ORIGINS contains '*' with credentials enabled — browsers will "
        "reject the session cookie. Set CORS_ORIGINS to explicit origins."
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ────────────────────────────────────────────────────────────────
# ``/auth/*`` is public by construction (it is how you get a session). Every
# other endpoint hangs off ``api``, whose router-level dependency makes
# "forgot to add the gate" impossible for anything registered here.
app.include_router(auth_router)

api = APIRouter(dependencies=[Depends(require_user)])


@app.exception_handler(StarletteHTTPException)
async def _expired_session_clears_the_cookie(request: Request, exc: StarletteHTTPException):
    """Drop a dead session cookie on any 401.

    Without this a browser keeps presenting a token the server has already
    rejected (expired, revoked, or from a wiped dev database) on every single
    request, and every one of them pays a database lookup to be told no.
    """
    response = await http_exception_handler(request, exc)
    if exc.status_code == 401:
        _clear_session_cookie(response)
    return response

# ── Session lifecycle helpers ───────────────────────────────────────────

# Lock to prevent concurrent session creation for the same thread_id.
_creation_lock = asyncio.Lock()

# In-flight agent runner tasks. Each chat-stream request schedules its
# agent loop as a detached asyncio.Task (so sse-starlette cancelling the
# response on client-disconnect — see sse.py:479 cancel_on_finish — does
# NOT kill the agent loop). The task is added to this set so Python's GC
# keeps a strong reference until it self-removes via a done_callback.
# Lets `len(_active_runs)` serve as a quick observability probe.
_active_runs: set[asyncio.Task[Any]] = set()

# Tool-result truncation bound. Applied both on the SSE wire and when the
# call is persisted, so a thread export matches what the user watched
# stream by.
# ponytail: flat cap; make it per-tool if a large file read gets clipped.
_TOOL_RESULT_MAX = 2000

# ── Per-thread run contexts (v3 multi-subscriber model) ────────────────
# Each in-flight chat run has a RunContext keyed by thread_id. The runner
# fans events into the context's `history` AND every subscriber queue;
# any SSE consumer (initial /chat/stream caller, OR a later /chat/resume
# re-attach) replays the history and then tails live events from its own
# queue. The `_seq` counter on each event lets a re-subscriber dedup the
# overlap between snapshot replay and queue-buffered tail.
#
# Lifetime: created at the start of `/chat/stream`, cleaned up
# `_RUN_CONTEXT_CLEANUP_DELAY` seconds after the runner finishes so a
# late re-attaching consumer still sees the final `done` event.

@dataclass
class RunContext:
    """Buffered event log + multi-subscriber fan-out for one agent run."""

    history: list[dict[str, Any]] = field(default_factory=list)
    subscribers: set[asyncio.Queue[dict[str, Any] | None]] = field(
        default_factory=set
    )
    seq: int = 0
    finished: bool = False

_run_contexts: dict[str, RunContext] = {}

# Keep the context around for a short grace window after the runner
# finishes — a re-attaching consumer can still replay the full history
# (including the `done` event) within this window. 60 s is long enough
# for a hand-back-to-foreground tab to catch up, short enough not to
# accumulate stale contexts on a busy server.
_RUN_CONTEXT_CLEANUP_DELAY = 60.0

async def _cleanup_run_context(thread_id: str, delay: float = _RUN_CONTEXT_CLEANUP_DELAY) -> None:
    """Evict a finished RunContext after `delay` seconds."""
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return
    _run_contexts.pop(thread_id, None)

async def _get_or_create_session(thread_id: str) -> _SessionEntry:
    """Return the (agent, backend) for *thread_id*, creating one if needed.

    On first call after a server restart, ``create_orchestrator`` builds a
    DockerBackend with a deterministic name (``harness-<thread_id>``); the
    backend's ``_ensure_container`` then reattaches to the existing
    stopped container instead of creating a new one.

    Container creation is run in a thread pool so the event loop stays
    free for other requests (SSE streaming, artifact reads, etc.).
    Without this, ``docker run`` can block for 5-15 seconds on Windows,
    freezing the entire server.
    """
    if thread_id in _sessions:
        return _sessions[thread_id]

    # Serialise creation: if two requests for the same thread arrive
    # simultaneously, the second one waits for the first to finish rather
    # than creating two competing containers.
    async with _creation_lock:
        # Double-check after acquiring the lock
        if thread_id in _sessions:
            return _sessions[thread_id]

        logger.info("Creating/attaching session container for thread_id=%s", thread_id)
        loop = asyncio.get_running_loop()
        agent, backend = await loop.run_in_executor(
            None,  # use default thread pool (separate from docker-exec pool)
            create_orchestrator,
            thread_id,
        )
        _sessions[thread_id] = (agent, backend)

        cid = backend._cid
        if cid:
            logger.info(
                "Session %s → container %s",
                thread_id,
                cid[:12] if cid else "?",
            )

        return agent, backend

def _destroy_session(thread_id: str) -> bool:
    """Stop and remove the Docker container for *thread_id*.

    Looks in two places, in order:
      1. In-memory `_sessions` dict (live session in this process).
      2. Docker by deterministic container name (`harness-<thread_id>`) —
         catches the case where the chat's container was created in a
         previous backend process, kept on disk by the shutdown handler,
         and is being deleted before any new chat message re-adopted it.

    Returns True if a container was found and removed.
    """
    entry = _sessions.pop(thread_id, None)
    if entry is not None:
        _agent, backend = entry
        cid = backend._cid
        backend.close(remove=True)
        logger.info(
            "Destroyed session %s → container %s stopped and removed",
            thread_id,
            cid[:12] if cid else "?",
        )
        return True

    # No live session — fall back to a name-based Docker lookup so dormant
    # containers from previous backend processes still get cleaned up.
    name = container_name_for(thread_id)
    probe = DockerBackend(container_name=name, auto_create=False)
    cid, _running = probe._find_by_name(name)
    if cid is None:
        logger.info(
            "No session or container found for thread_id=%s — nothing to destroy",
            thread_id,
        )
        return False

    # Adopt the discovered container. `_started` MUST be set: close() early
    # -returns when `not self._started`, so without this the stop/remove is
    # silently skipped and the sandbox is leaked. (`_find_by_name` only sets
    # `_cid` via our assignment; it never marks the probe as started.)
    probe._cid = cid
    probe._started = True
    probe.close(remove=True)
    logger.info(
        "Destroyed dormant container for thread_id=%s → %s stopped and removed",
        thread_id,
        cid[:12],
    )
    return True

def _invalidate_all_orchestrators(reason: str) -> int:
    """Drop every cached (agent, backend) tuple so the next message in each
    thread rebuilds its orchestrator with a fresh subagent roster.

    Containers are left running on disk; the rebuilt orchestrator constructs
    a new DockerBackend with the same deterministic container name and
    re-adopts the existing container, so workspace state (artifacts,
    uploaded files, diagram outputs) survives untouched.

    In-flight /chat/stream requests keep their own reference to the old
    agent for the duration of the response — only subsequent messages see
    the rebuilt orchestrator.

    Returns the number of sessions invalidated.
    """
    count = len(_sessions)
    if count == 0:
        return 0
    _sessions.clear()
    logger.info(
        "Invalidated %d session orchestrator(s) — reason: %s", count, reason
    )
    return count

def _stop_session_keep_container(thread_id: str) -> bool:
    """Stop the container but leave it on disk so it can be restarted later.

    Used by the lifespan shutdown handler — chats still exist in the
    frontend's localStorage, so their containers must persist so workspace
    data (artifacts, diagrams, outputs) survives the restart.
    """
    entry = _sessions.pop(thread_id, None)
    if entry is None:
        return False

    _agent, backend = entry
    cid = backend._cid
    backend.close(remove=False)
    logger.info(
        "Stopped (kept) container for session %s → %s",
        thread_id,
        cid[:12] if cid else "?",
    )
    return True

def _session_count() -> int:
    """Return the number of active sessions."""
    return len(_sessions)

# ── Ownership ───────────────────────────────────────────────────────────
# A conversation id IS a thread id IS a container suffix, so authorising the
# thread id authorises the sandbox behind it. Both "no such row" and "someone
# else's row" answer 404 on purpose: a 403 would confirm that another user's
# conversation exists.

_CONVERSATION_NOT_FOUND = "Conversation not found"


def _assert_owns(conv: Any, user: CurrentUser) -> Any:
    """Raise 404 unless *conv* belongs to *user*."""
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail=_CONVERSATION_NOT_FOUND)
    return conv


async def _owned_conversation(
    thread_id: str,
    user: CurrentUser,
    *,
    required: bool = False,
) -> Any:
    """Authorise a thread id before it reaches Docker.

    ``required=False`` is for the sandbox endpoints (/projects, /upload,
    /chat): the row is normally created by the client first, but a chat that
    starts before its row exists is legitimate, so a *missing* row is allowed
    there. An *existing* row owned by someone else — including a legacy row
    with ``user_id IS NULL`` — is always a 404, which is what stops a new
    account from reattaching to a pre-auth container by guessing its id.
    """
    async with session_scope() as session:
        conv = await conversations_store.get_conversation(session, thread_id)
    if conv is None:
        if required:
            raise HTTPException(status_code=404, detail=_CONVERSATION_NOT_FOUND)
        return None
    return _assert_owns(conv, user)

# ── Health ──────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check — reports number of active session containers."""
    count = _session_count()
    return HealthResponse(
        status="ok",
        container_id=None,
        container_running=True,
    )

@api.get("/tracing", response_model=TracingStatusResponse)
async def tracing_status():
    """Return LangSmith tracing configuration and connectivity status."""
    info = _tracing_info
    return TracingStatusResponse(
        enabled=is_tracing_enabled(),
        project=info.get("project", ""),
        endpoint=info.get("endpoint", ""),
        status=info.get("status", "disabled"),
        api_key_set=info.get("api_key_set", False),
    )

# ── Projects ───────────────────────────────────────────────────────────

@api.post("/projects", response_model=ProjectCreateResponse)
async def create_project(
    req: ProjectCreateRequest,
    thread_id: str = Query(
        default="default",
        description="Chat thread whose container should host this workspace.",
    ),
    user: CurrentUser = Depends(require_user),
):
    """Create a new project workspace inside the chat's container."""
    await _owned_conversation(thread_id, user)
    _agent, backend = await _get_or_create_session(thread_id)
    ws = ProjectWorkspace(req.project_id, backend)
    ws.init_directories()
    ws.init_project_graph()

    return ProjectCreateResponse(
        project_id=req.project_id,
        root=ws.root,
        status="created",
    )

_PIPELINE_BARE_TO_PATH = {
    "REQUIREMENTS.md": "requirements/REQUIREMENTS.md",
    "GLOSSARY.md": "requirements/GLOSSARY.md",
    "CONSTRAINTS.md": "requirements/CONSTRAINTS.md",
    "USER_STORIES.md": "requirements/USER_STORIES.md",
    "ACCEPTANCE_CRITERIA.md": "requirements/ACCEPTANCE_CRITERIA.md",
    "ARCHITECTURE.md": "design/ARCHITECTURE.md",
    "DATA_MODEL.md": "design/DATA_MODEL.md",
    "ADR.md": "design/ADR.md",
    "API_SPEC.md": "design/API_SPEC.md",
    "openapi.yaml": "design/openapi.yaml",
    "BACKLOG.md": "planning/BACKLOG.md",
    "TEST_PLAN.md": "planning/TEST_PLAN.md",
    "CI_CD.md": "planning/CI_CD.md",
    "ci/pipeline.yml": "planning/ci/pipeline.yml",
    "sequence.mmd": "diagrams/sequence.mmd",
    "class.mmd": "diagrams/class.mmd",
    "state.mmd": "diagrams/state.mmd",
    "erd.mmd": "diagrams/erd.mmd",
    "deployment.mmd": "diagrams/deployment.mmd",
}

_LANG_BY_EXT = {
    "md": "markdown",
    "mmd": "mermaid",
    "feature": "gherkin",
    "html": "html",
    "htm": "html",
    "json": "json",
    "yml": "yaml",
    "yaml": "yaml",
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "txt": "text",
    "csv": "csv",
    "xml": "xml",
    "log": "text",
}

# Hard cap on inline read size — large blobs lock up the browser when
# dropped into a single <pre>. Anything bigger is reported as too-large.
_MAX_READ_BYTES = 1024 * 1024

def _resolve_project_path(ws: ProjectWorkspace, rel_path: str) -> str:
    """Map a user-supplied relative path to an absolute container path.

    Rejects empty paths, absolute paths, and any segment that would escape
    the project root via `..`. Also remaps bare PIPELINE artifact names
    (e.g. ``REQUIREMENTS.md``) to their full subpath so the
    legacy pipeline-click URLs keep working.
    """
    if rel_path is None:
        rel_path = ""
    rel_path = rel_path.strip().lstrip("/")

    # Strip absolute sandbox root prefix if present
    if rel_path.startswith(ws.root):
        rel_path = rel_path[len(ws.root):]
    elif rel_path.startswith(ws.root.lstrip("/")):
        rel_path = rel_path[len(ws.root.lstrip("/")):]
    rel_path = rel_path.lstrip("/")

    # Pipeline shortcut — keep the front-end click flow working unchanged.
    if rel_path in _PIPELINE_BARE_TO_PATH:
        rel_path = _PIPELINE_BARE_TO_PATH[rel_path]

    # Reject path-traversal attempts. We compare segment-by-segment rather
    # than using posixpath.normpath, which would silently collapse
    # `foo/../../bar` into something inside the project but still let a
    # crafted absolute prefix slip through.
    segments = [s for s in rel_path.split("/") if s not in ("", ".")]
    for seg in segments:
        if seg == "..":
            raise HTTPException(status_code=400, detail="Path may not contain '..'")
    safe_rel = "/".join(segments)
    return f"{ws.root}/{safe_rel}" if safe_rel else ws.root

@api.get("/projects/{project_id}/files")
async def list_project_files(
    project_id: str,
    path: str = Query(default="", description="Path relative to the project root. Empty = root."),
    thread_id: str = Query(default="default", description="Chat thread whose container to query."),
    user: CurrentUser = Depends(require_user),
):
    """Return the entries of a directory inside the project workspace.

    Used by the frontend file explorer to navigate /workspace/project_<id>/
    freely (instead of being limited to the hardcoded artifact list).
    Hidden entries (`.` prefix) are skipped.
    """
    await _owned_conversation(thread_id, user)
    _agent, backend = await _get_or_create_session(thread_id)
    ws = ProjectWorkspace(project_id, backend)
    target = _resolve_project_path(ws, path)

    # `find -maxdepth 1 -printf` lists each child with type+size+mtime in
    # one shot. Cheaper than ls + stat per file and avoids parsing locale-
    # dependent ls output. `%y` is one char: f/d/l, `%s` is bytes,
    # `%T@` is epoch seconds.
    cmd = (
        f"test -d {target} && cd {target} && "
        "find . -mindepth 1 -maxdepth 1 -printf '%y\\t%s\\t%T@\\t%P\\n' "
        "| sort -k4"
    )
    # Run the find + stat via async wrapper so the event loop stays
    # responsive during agent streaming.
    result = await backend.execute_async(cmd)
    if result.exit_code != 0:
        raise HTTPException(
            status_code=404,
            detail=f"Directory not found: {path or '(root)'}",
        )

    entries: list[dict[str, Any]] = []
    for line in (result.output or "").splitlines():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        typ, size_str, mtime_str, name = parts
        if name.startswith("."):
            continue  # skip dotfiles/dirs (.cache, .pytest_cache, etc.)
        try:
            size = int(size_str)
            mtime = float(mtime_str)
        except ValueError:
            continue
        entries.append({
            "name": name,
            "type": "dir" if typ == "d" else "file",
            "size": size,
            "mtime": mtime,
        })

    return {
        "project_id": project_id,
        "path": path.strip("/"),
        "entries": entries,
    }

@api.get("/projects/{project_id}/artifacts/{artifact_name:path}")
async def get_artifact_content(
    project_id: str,
    artifact_name: str,
    thread_id: str = Query(default="default", description="Chat thread to read from."),
    user: CurrentUser = Depends(require_user),
):
    """Fetch the content of a file inside the project workspace.

    Accepts any path under the project root.  Text files are read via
    ``cat`` and returned as-is.  Binary documents (.docx, .pdf, .xlsx)
    are converted to HTML for in-browser preview via the sandboxed
    iframe in ArtifactCanvas.

    Docker operations are routed through the dedicated exec thread pool
    (execute_async / download_file_async) so the event loop stays free.
    """
    await _owned_conversation(thread_id, user)
    _agent, backend = await _get_or_create_session(thread_id)
    ws = ProjectWorkspace(project_id, backend)
    container_path = _resolve_project_path(ws, artifact_name)

    ext = artifact_name.rsplit(".", 1)[-1].lower() if "." in artifact_name else ""

    # ── Binary documents → convert to HTML ──────────────────────────
    _binary_exts = {"docx", "pdf", "xlsx", "xls"}
    if ext in _binary_exts:
        raw = await backend.download_file_async(container_path)
        if raw is None:
            raise HTTPException(status_code=404, detail=f"File not found: {artifact_name}")
        if len(raw) > _MAX_READ_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"File too large to preview ({len(raw)} bytes; limit "
                    f"{_MAX_READ_BYTES})."
                ),
            )
        html = preview_binary(ext, raw)
        if html is None:
            raise HTTPException(
                status_code=415,
                detail=f"No preview converter for .{ext} files",
            )
        return {
            "project_id": project_id,
            "name": artifact_name,
            "language": "html",
            "content": html,
            "size": len(html),
        }

    # ── Text files ──────────────────────────────────────────────────
    # Size-check before reading to avoid pulling tens of MB into the
    # response on a misclick.
    size_result = await backend.execute_async(
        f"stat -c '%s' {container_path} 2>/dev/null"
    )
    if size_result.exit_code != 0 or not size_result.output.strip().isdigit():
        raise HTTPException(status_code=404, detail=f"File not found: {artifact_name}")
    size = int(size_result.output.strip())
    if size > _MAX_READ_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large to preview ({size} bytes; limit "
                f"{_MAX_READ_BYTES}). Download via the container directly."
            ),
        )

    result = await backend.execute_async(
        f"cat {container_path} 2>/dev/null"
    )
    if result.exit_code != 0:
        raise HTTPException(status_code=404, detail=f"File not found: {artifact_name}")

    lang = _LANG_BY_EXT.get(ext, "text")

    return {
        "project_id": project_id,
        "name": artifact_name,
        "language": lang,
        "content": result.output,
        "size": len(result.output),
    }

# ── File download (raw + markdown-to-PDF) ──────────────────────────────

# Higher cap than _MAX_READ_BYTES (which guards the preview) — downloads
# bypass the in-memory preview render and stream straight back to the
# client, so we can afford a more generous limit. Anything beyond this
# should be pulled out of the container via `docker cp` manually.
_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

# Browser-friendly content types for the formats users commonly download.
_DOWNLOAD_MIME = {
    "md": "text/markdown; charset=utf-8",
    "txt": "text/plain; charset=utf-8",
    "json": "application/json",
    "html": "text/html; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "xml": "application/xml",
    "yaml": "application/yaml",
    "yml": "application/yaml",
    "py": "text/x-python",
    "js": "application/javascript",
    "ts": "application/typescript",
    "pdf": "application/pdf",
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
    "xls": "application/vnd.ms-excel",
    "mmd": "text/plain; charset=utf-8",
}

def _content_disposition(filename: str) -> str:
    """Build a Content-Disposition header that handles non-ASCII names safely.

    Uses RFC 5987 ``filename*`` so unicode names survive correctly, with a
    plain ``filename=`` ASCII fallback for older clients.
    """
    from urllib.parse import quote

    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "download"
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"

@api.get("/projects/{project_id}/download")
async def download_artifact(
    project_id: str,
    path: str = Query(..., description="Path relative to the project root."),
    thread_id: str = Query(default="default", description="Chat thread to read from."),
    as_format: str | None = Query(default=None, alias="as", description="Optional conversion: 'pdf' for markdown sources."),
    user: CurrentUser = Depends(require_user),
):
    """Stream a file from the project workspace as a browser download.

    Two modes:
      * Default — return the raw file bytes with an attachment header.
      * ``?as=pdf`` and the source is markdown — render the markdown via
        ``markdown-pdf`` and stream the resulting PDF. Other source types
        are rejected with 400 (we don't claim to convert arbitrary
        formats).

    Conversion runs in the dedicated exec thread pool so the event loop
    stays free during a heavy render.
    """
    from fastapi.responses import Response

    await _owned_conversation(thread_id, user)
    _agent, backend = await _get_or_create_session(thread_id)
    ws = ProjectWorkspace(project_id, backend)
    container_path = _resolve_project_path(ws, path)

    raw = await backend.download_file_async(container_path)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if len(raw) > _MAX_DOWNLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large to download via the API ({len(raw)} bytes; "
                f"limit {_MAX_DOWNLOAD_BYTES})."
            ),
        )

    src_ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    basename = path.rsplit("/", 1)[-1] or "download"

    # ── Markdown → PDF conversion ───────────────────────────────────
    if as_format and as_format.lower() == "pdf":
        if src_ext != "md":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"`as=pdf` only supports markdown sources, got .{src_ext or '?'}."
                ),
            )
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Markdown source isn't valid UTF-8: {exc}",
            ) from exc

        # Render PDF off the event loop — the conversion is CPU-bound and
        # can take ~hundreds of ms for long reports.
        from sdlc.services.document_preview import markdown_to_pdf

        loop = asyncio.get_running_loop()
        try:
            pdf_bytes = await loop.run_in_executor(
                None,
                lambda: markdown_to_pdf(text, title=basename),
            )
        except RuntimeError as exc:
            # markdown-pdf import failure surfaces here — actionable.
            raise HTTPException(status_code=501, detail=str(exc)) from exc

        pdf_name = basename.rsplit(".", 1)[0] + ".pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": _content_disposition(pdf_name)},
        )

    # ── Raw download ────────────────────────────────────────────────
    media_type = _DOWNLOAD_MIME.get(src_ext, "application/octet-stream")
    return Response(
        content=raw,
        media_type=media_type,
        headers={"Content-Disposition": _content_disposition(basename)},
    )

@api.get("/projects/{project_id}/artifacts", response_model=ArtifactListResponse)
async def list_artifacts(
    project_id: str,
    thread_id: str = Query(default="default", description="Chat thread to list artifacts for."),
    user: CurrentUser = Depends(require_user),
):
    """List all artifacts in a project and their existence status."""
    await _owned_conversation(thread_id, user)
    _agent, backend = await _get_or_create_session(thread_id)
    ws = ProjectWorkspace(project_id, backend)

    # Quick check: does project directory exist?  Auto-create on demand so
    # the Inspector can show the full pipeline (all artifacts as "pending")
    # even before the first chat message has been sent.
    # Run in thread pool to avoid blocking the event loop during streaming.
    result = await backend.execute_async(
        f"test -d {ws.root} && echo yes || echo no"
    )
    if "no" in result.output:
        ws.init_directories()
        ws.init_project_graph()

    # ── Cache check ───────────────────────────────────────────────────
    # Frontend polls every 2s; without caching, each poll fires a batch
    # Docker exec.  The cache serves stale results for up to
    # ARTIFACT_CACHE_TTL seconds (default 1s), cutting Docker calls
    # roughly in half while still feeling "live".
    cache_key = f"{project_id}:{thread_id}"
    now = time.monotonic()
    if cache_key in _artifact_cache:
        cached_ts, cached_data = _artifact_cache[cache_key]
        if now - cached_ts < ARTIFACT_CACHE_TTL:
            return ArtifactListResponse(
                project_id=project_id,
                artifacts=cached_data,
            )

    # Reverse mapping: phase-qualified artifact path → agent
    reverse = {}
    for agent_name, art_list in AGENT_ARTIFACTS.items():
        for art in art_list:
            reverse[art] = agent_name

    # Phase-qualified paths are the single source of truth — they match the
    # on-disk layout (requirements/REQUIREMENTS.md, design/openapi.yaml, etc.)
    # and the keys used by AGENT_ARTIFACTS / DEFAULT_PROJECT_GRAPH.
    all_artifact_paths = expected_artifact_paths()

    # Walk the entire workspace, not just the expected-artifact list — agents
    # are free to create files outside that catalogue and the index needs to
    # surface them too. See artifacts.scan_workspace_files for the exclusions.
    files_info = await scan_workspace_files(ws)
    existing_files = set(files_info.keys())

    artifacts = []
    for art_path in all_artifact_paths:
        exists = art_path in existing_files
        agent = reverse.get(art_path, "")
        phase = art_path.split("/", 1)[0]
        artifacts.append({
            "name": art_path,
            "phase": phase,
            "status": "ready" if exists else "pending",
            "agent": agent,
        })

    # Root-level bookkeeping artifacts (log.md) live at the project root, not
    # under a phase folder. List them at their real path so the read endpoint
    # resolves them; group under "sources" for display.
    for root_art in ROOT_ARTIFACTS:
        artifacts.append({
            "name": root_art,
            "phase": "sources",
            "status": "ready" if root_art in existing_files else "pending",
            "agent": "",
        })

    # Dynamically append any other files present in the workspace
    expected_set = set(all_artifact_paths) | set(ROOT_ARTIFACTS)
    valid_phases = {"sources", "requirements", "design", "planning", "diagrams"}
    for existing_file in sorted(existing_files):
        if existing_file in expected_set:
            continue
        # Exclude index.md or metadata files defensively
        if existing_file == "index.md" or existing_file.startswith("metadata/") or existing_file.endswith(".keep"):
            continue

        # Determine phase based on first path component
        parts = existing_file.split("/", 1)
        phase = parts[0] if len(parts) > 1 else "sources"
        if phase not in valid_phases:
            phase = "sources"

        # Determine agent
        agent = reverse.get(existing_file, "")
        if not agent and "/diagrams/" in existing_file:
            agent = "diagram"

        artifacts.append({
            "name": existing_file,
            "phase": phase,
            "status": "ready",
            "agent": agent,
        })

    # Mtime-based change detection — regenerate index.md only when the
    # observed (path, mtime) signature differs from the last write. This
    # keeps the poll cheap while still surfacing every artifact change to
    # the user's index page within one poll tick.
    mtime_sig = frozenset((p, mt) for p, (_, mt) in files_info.items())
    previous_sig = _artifact_index_sig.get(cache_key)
    if mtime_sig != previous_sig:
        try:
            await regenerate_index(ws, files_info)
            _artifact_index_sig[cache_key] = mtime_sig
        except Exception:
            logger.exception("Failed to regenerate index.md for %s", cache_key)

    # Cache the result so the next poll within ARTIFACT_CACHE_TTL
    # (default 1s) skips the Docker exec entirely.
    _artifact_cache[cache_key] = (time.monotonic(), artifacts)

    return ArtifactListResponse(project_id=project_id, artifacts=artifacts)

# ── Chat (non-streaming) ───────────────────────────────────────────────

@api.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user: CurrentUser = Depends(require_user)):
    await _owned_conversation(req.thread_id, user)
    agent, _backend = await _get_or_create_session(req.thread_id)
    config = {"configurable": {"thread_id": req.thread_id}}

    # Enrich config with LangSmith metadata so every LLM call is tagged
    if is_tracing_enabled():
        config["metadata"] = make_trace_metadata(req.project_id, req.thread_id)
        config["tags"] = ["orchestrator", f"project:{req.project_id}"]

    user_content = _build_user_content(req)

    # LangSmith tracing happens automatically via env vars — no wrapper
    # needed. Project/thread tags are already in config["metadata"].
    result = agent.invoke(
        {"messages": [HumanMessage(content=user_content)]},
        config=config,
    )

    # Extract the last AI message
    ai_text = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "type") and msg.type == "ai":
            ai_text = msg.content
            break
        if hasattr(msg, "role") and msg.role == "assistant":
            ai_text = msg.content
            break

    # Attach trace URL to response metadata
    response = ChatResponse(
        message=ai_text, thread_id=req.thread_id, project_id=req.project_id
    )
    return response

# ── Chat (SSE streaming) ──────────────────────────────────────────────

async def _record_run_changes(
    ws: ProjectWorkspace,
    before_files: dict[str, tuple[int, int]],
) -> None:
    """Deterministically record artifact changes from one agent run.

    Diffs the workspace inventory captured before the run against the state
    after it, then:

      * appends a row to ``log.md`` per changed artifact (``produce`` for new
        files, ``update`` for re-written ones, ``remove`` for deletions;
        ``upload`` for new files under ``sources/``),
      * writes one ``lineage.json`` entry per agent whose mapped outputs
        changed, and
      * regenerates ``index.md`` from the fresh inventory.

    The LLM is never responsible for this bookkeeping — it runs server-side so
    the OKF change-history and lineage can't be forgotten. Callers must wrap
    this so a failure here never breaks the user-facing stream.
    """
    after_files = await scan_workspace_files(ws)

    # Classify each path that differs between the two snapshots.
    log_rows: list[tuple[str, str, str]] = []
    changed_outputs: dict[str, list[str]] = {}  # agent → outputs produced/updated

    # Files that actually exist in the workspace, either now or before this
    # run (a removal's dependency may itself have been removed).
    known_files = set(after_files) | set(before_files)

    def _source_for(path: str) -> str:
        """Declared upstream dependency, but ONLY if that file really exists.

        DEFAULT_PROJECT_GRAPH carries generic placeholder dependencies
        (``sources/box.xlsx``, ``sources/requirements.pdf``, ...). Printing
        them unconditionally wrote provenance for files that were never
        uploaded: a project whose real inputs are
        ``Morphologischer_Kasten_Lagertechnologien.xlsx`` got a log row
        claiming BOX.md came from ``sources/box.xlsx``.

        That matters because the prompts tell every agent log.md is the
        authoritative history to consult for what changed and where it came
        from — so the harness was feeding its own agents invented provenance
        about their inputs, underneath the anti-fabrication rules. A diff of
        two file snapshots cannot observe which input was actually read, so
        the honest options are "a declared dependency that demonstrably
        exists" or nothing. Anything unverifiable prints ``-``.
        """
        deps = DEFAULT_PROJECT_GRAPH.get(path, {}).get("depends_on", [])
        for dep in deps:
            if dep in known_files:
                return dep
        return "-"

    for path, (_size, mtime) in after_files.items():
        prev = before_files.get(path)
        if prev is None:
            action = "upload" if path.startswith("sources/") else "produce"
        elif mtime > prev[1]:
            action = "update"
        else:
            continue  # unchanged
        log_rows.append((action, _source_for(path), path))
        agent = ARTIFACT_AGENT.get(path)
        if agent:
            changed_outputs.setdefault(agent, []).append(path)

    # Deletions — present before, gone after.
    for path in before_files:
        if path not in after_files:
            log_rows.append(("remove", _source_for(path), path))

    if not log_rows:
        return

    await ws.append_log_rows(log_rows)

    # One lineage entry per agent that produced/updated mapped artifacts.
    for agent, outputs in changed_outputs.items():
        inputs: list[str] = []
        for out in outputs:
            for dep in DEFAULT_PROJECT_GRAPH.get(out, {}).get("depends_on", []):
                if dep not in inputs:
                    inputs.append(dep)
        ws.write_lineage_entry(agent, inputs_used=inputs, outputs_produced=outputs)

    # Refresh index.md immediately at run end (otherwise it only updates on
    # the frontend's next artifact poll).
    await regenerate_index(ws, after_files)

def _build_user_content(req: ChatRequest) -> str:
    """Build the user message with project context and file-upload annotations.

    Injects project-id info and a readable file list so the agent knows what
    files are already available in the sandbox when the user doesn't re-state
    them in the message text.
    """
    user_msg = req.message or ""
    is_plan_mode = user_msg.strip().lower().startswith("/plan")

    if is_plan_mode:
        cleaned_msg = user_msg.strip()
        if cleaned_msg.lower().startswith("/plan "):
            cleaned_msg = cleaned_msg[len("/plan "):].strip()
        elif cleaned_msg.lower() == "/plan":
            cleaned_msg = ""

        planning_instruction = (
            "[PLANNING MODE ACTIVE]\n"
            "You are running in Plan Mode. Your objective is to map out the requested task "
            "and ask the user clarifying questions using the `ask_question` tool "
            "to resolve any ambiguities before proceeding with implementation.\n"
            "Do NOT perform implementation steps or summon subagents yet. "
            "First, list the initial plan/approach, call the `ask_question` tool "
            "to ask for clarification, and then stop generating to wait for the user's response.\n\n"
            f"User Goal: {cleaned_msg}"
        )
        msg_to_inject = planning_instruction
    else:
        msg_to_inject = user_msg

    context_parts: list[str] = []
    if req.project_id and req.project_id != "default":
        context_parts.append(f"Project ID: {req.project_id}")
    if req.uploaded_files:
        file_entries = [
            f"  - {req.file_names[i] or p.rsplit('/', 1)[-1]} -> {p}"
            if i < len(req.file_names)
            else f"  - {p.rsplit('/', 1)[-1]} -> {p}"
            for i, p in enumerate(req.uploaded_files)
        ]
        context_parts.append(
            "The user has uploaded the following files into the project workspace:\n"
            + "\n".join(file_entries)
            + "\n\n"
            "These files are available inside the Docker sandbox at the paths listed above.\n"
            "Use shell commands (cat, head, file, etc.) in the sandbox to read them.\n"
            "If the user has not specified what to do, suggest invoking @Ingestion to process the files.\n"
        )
    if context_parts:
        return "\n\n".join(context_parts) + "\n\n" + msg_to_inject
    return msg_to_inject

# ── Replay suppression ───────────────────────────────────────────────────
# A run that dies mid-execution (backend restart, container recycle, provider
# outage) leaves pending writes behind. The next invoke on the same thread_id
# resumes from that checkpoint and REPLAYS the interrupted work, re-emitting
# messages already in the transcript. On the wire they are indistinguishable
# from new output: the client's `_seq` dedup cannot catch them, because they
# are genuinely new events in a genuinely new run. Only the *identity* of the
# work says otherwise, so identity is what gets filtered.
#
# Two identity sets are needed, not one. A replayed tool result arrives as a
# fresh `ToolMessage` (new `id`) that reuses the `tool_call_id` of a call
# already in the transcript, so a message-id-only filter misses every replayed
# tool block: exactly the "tool calls reappear" half of the bug.

def _identities_from_state(messages: Any) -> tuple[set[str], set[str]]:
    """Return ``(message_ids, tool_call_ids)`` carried by *messages*.

    Reads whatever shape it is handed: LangChain messages from the checkpoint
    snapshot, where tool calls live on ``AIMessage.tool_calls`` and tool results
    carry ``tool_call_id``.
    """
    message_ids: set[str] = set()
    tool_call_ids: set[str] = set()
    for m in messages or []:
        mid = getattr(m, "id", None)
        if mid:
            message_ids.add(str(mid))
        tcid = getattr(m, "tool_call_id", None)
        if tcid:
            tool_call_ids.add(str(tcid))
        for tc in getattr(m, "tool_calls", None) or []:
            if isinstance(tc, dict) and tc.get("id"):
                tool_call_ids.add(str(tc["id"]))
    return message_ids, tool_call_ids

def _tool_ids_from_persisted(rows: Any) -> set[str]:
    """Tool-call ids already in the Postgres transcript for this thread.

    The fallback identity, used when the checkpoint snapshot cannot be read. It
    is a different shape from the in-state one: these rows carry the frontend's
    camelCase ``toolId`` rather than LangChain ``tool_calls``, and their integer
    ``id`` is not a LangChain message id, so only the tool ids transfer.
    """
    tool_call_ids: set[str] = set()
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        for tc in r.get("tool_calls") or []:
            if isinstance(tc, dict):
                tcid = tc.get("toolId") or tc.get("tool_call_id") or tc.get("id")
                if tcid:
                    tool_call_ids.add(str(tcid))
    return tool_call_ids

async def _load_replay_identity(
    agent: Any, config: dict[str, Any], thread_id: str
) -> tuple[set[str], set[str]]:
    """Best-effort identity of the work already in this thread's transcript.

    The checkpoint snapshot is primary: it is exact and it carries the message
    ids. If it cannot be read, or yields nothing, the persisted transcript in
    Postgres is the fallback, because it still carries the tool ids a replay
    would reuse. Streaming blind whenever the snapshot is unavailable is what
    repainted a whole conversation into the UI, so a failure here must narrow
    what gets emitted, never widen it.
    """
    message_ids: set[str] = set()
    tool_call_ids: set[str] = set()
    try:
        snap = await agent.aget_state(config)
        values = getattr(snap, "values", None)
        messages = values.get("messages") if isinstance(values, dict) else None
        message_ids, tool_call_ids = _identities_from_state(messages)
    except Exception:
        logger.warning(
            "Could not snapshot prior state for thread_id=%s — "
            "falling back to the persisted transcript",
            thread_id,
            exc_info=True,
        )

    if not message_ids and not tool_call_ids:
        try:
            async with session_scope() as session:
                rows = await conversations_store.list_messages(session, thread_id)
            tool_call_ids = _tool_ids_from_persisted(rows)
        except Exception:
            logger.warning(
                "Persisted-transcript fallback failed for thread_id=%s",
                thread_id,
                exc_info=True,
            )

    return message_ids, tool_call_ids

def _chunk_already_persisted(
    chunk: Any, message_ids: set[str], tool_call_ids: set[str]
) -> bool:
    """Was everything this chunk carries already in the transcript?

    True when the chunk *is* a prior message, *is* a prior tool result, or is an
    assistant message whose entire tool-call batch is prior calls. The third
    case is the narrow one: a message id that is new while every tool-call id is
    not, which is what a partially-replayed assistant turn looks like.

    Deliberately narrows to ``False`` on any error. Unlike the snapshot read
    (where failing open repainted a conversation), a single unrecognisable chunk
    is a display detail, and this runs inside the stream loop: raising here
    would abort a live run over a cosmetic check. ``tool_calls`` in particular
    is a derived property on a streaming chunk and can throw while the argument
    JSON is still incomplete.
    """
    try:
        mid = getattr(chunk, "id", None)
        if mid and str(mid) in message_ids:
            return True
        tcid = getattr(chunk, "tool_call_id", None)
        if tcid and str(tcid) in tool_call_ids:
            return True
        tool_calls = getattr(chunk, "tool_calls", None) or []
        return bool(tool_calls) and all(
            isinstance(tc, dict) and tc.get("id") and str(tc["id"]) in tool_call_ids
            for tc in tool_calls
        )
    except Exception:  # noqa: BLE001 — a cosmetic guard must not kill a run
        return False

def _spawn_run(
    thread_id: str,
    agent: Any,
    config: dict[str, Any],
    ws: ProjectWorkspace,
    before_files: dict[str, tuple[int, int]],
    initial_input: Any,
) -> RunContext:
    """Create a RunContext + detached agent runner and register it.

    The runner streams the agent, persists, runs OKF bookkeeping, and
    self-cleans — independent of any HTTP response, so it survives client
    disconnects.
    """
    ctx = RunContext()
    _run_contexts[thread_id] = ctx

    def emit(payload: dict[str, Any]) -> None:
        """Fan-out a single SSE event to history + every active subscriber."""
        ctx.seq += 1
        event = {**payload, "_seq": ctx.seq}
        ctx.history.append(event)
        for q in list(ctx.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    async def agent_runner() -> None:
        assistant_content_buf: str = ""
        assistant_reasoning_buf: str = ""
        # Tool calls made during this run, keyed by tool_id so the streamed
        # name / args-delta / result events (three separate emit sites below)
        # land in one record. Insertion order == call order, so persisting
        # `.values()` keeps the transcript chronological without a second list.
        # Spans the whole run, subagents included: the export is a record of
        # everything the thread did, and each entry carries its own `agent`.
        assistant_tool_calls: dict[str, dict[str, Any]] = {}
        current_agent_field: str = ""  # "" = orchestrator
        # Cross-chunk state for inline <think>…</think> splitting.
        think_state: dict = {"in_think": False, "buf": ""}

        try:
            active_namespaces: set[str] = set()
            completed_namespaces: set[str] = set()
            subagent_names: dict[str, str] = {}

            # Subagent name resolution — improved approach.
            # We keep two mappings:
            # 1. task_tcid_to_name: tool_call_id → (subagent_name, description)
            #    Populated when we see the orchestrator's `task` tool call args.
            # 2. ns_to_tcid: namespace_key → tool_call_id
            #    Populated from LangGraph 'events' stream (tasks lifecycle).
            # Together these give us: namespace → tool_call_id → subagent_name.
            # Fallback: FIFO pop if exact resolution fails (with warning).
            task_args_buf: dict[str, str] = {}
            queued_task_ids: set[str] = set()
            pending_delegations: list[tuple[str, str]] = []
            task_tcid_to_name: dict[str, tuple[str, str]] = {}  # tcid → (name, desc)
            ns_to_tcid: dict[str, str] = {}  # ns_key → tool_call_id

            todos_buf: dict[str, str] = {}
            last_todos_sig: dict[str, str] = {}

            tc_index_to_id: dict[Any, str] = {}
            last_named_tcid: str = ""

            def _try_queue_task(tcid: str) -> None:
                if tcid in queued_task_ids or tcid not in task_args_buf:
                    return
                raw = task_args_buf[tcid]
                name = ""
                desc = ""
                try:
                    obj = json.loads(raw)
                    name = (obj.get("subagent_type") or "") if isinstance(obj, dict) else ""
                    desc = (obj.get("description") or "") if isinstance(obj, dict) else ""
                except json.JSONDecodeError:
                    m = SUBAGENT_TYPE_RE.search(raw)
                    if m:
                        name = m.group(1)
                        desc = _extract_task_field(raw, "description")
                if name:
                    pending_delegations.append((name, desc))
                    task_tcid_to_name[tcid] = (name, desc)
                    queued_task_ids.add(tcid)

            def _pop_delegation(ns_tuple: tuple, ns_key: str) -> tuple[str, str]:
                # (A) Exact match via events-driven ns_to_tcid mapping
                tcid = ns_to_tcid.get(ns_key)
                if tcid and tcid in task_tcid_to_name:
                    name, desc = task_tcid_to_name[tcid]
                    # Also remove from pending_delegations list
                    for i, (pn, pd) in enumerate(pending_delegations):
                        if pn == name:
                            pending_delegations.pop(i)
                            break
                    logger.info("_pop_delegation: exact match ns=%r → tcid=%s → agent=%s", ns_key, tcid, name)
                    return name, desc

                # (B) Substring heuristic on namespace parts
                ns_lower = [str(x).lower() for x in ns_tuple]
                for i, (name, desc) in enumerate(pending_delegations):
                    name_lower = name.lower()
                    if any(name_lower in ns_part or ns_part in name_lower for ns_part in ns_lower):
                        logger.info("_pop_delegation: substring match ns=%r → agent=%s", ns_key, name)
                        return pending_delegations.pop(i)

                # (C) FIFO fallback — log a warning so we can track occurrences
                if pending_delegations:
                    name, desc = pending_delegations.pop(0)
                    logger.warning(
                        "_pop_delegation: FIFO fallback ns=%r → agent=%s (no exact/substring match, may be wrong)",
                        ns_key, name,
                    )
                    return name, desc

                ns_last = ns_tuple[-1] if ns_tuple else "unknown"
                return ns_last, ""

            # ── Replay suppression ────────────────────────────────────
            # Identity of the work already in this thread's transcript BEFORE
            # this run starts. See the module-level note above _spawn_run for
            # why this exists, and why it needs two sets rather than one.
            replayed_ids, replayed_tool_ids = await _load_replay_identity(
                agent, config, thread_id
            )
            if replayed_ids or replayed_tool_ids:
                logger.info(
                    "Replay suppression armed for thread_id=%s: "
                    "%d prior message(s), %d prior tool call(s)",
                    thread_id,
                    len(replayed_ids),
                    len(replayed_tool_ids),
                )
            # Tell the client this run is a resume. It cannot infer that for
            # itself: the replayed events are genuinely new events in a new
            # run, so left unmarked its only option is to append them to a
            # transcript it already holds.
            emit({"event": "message", "data": json.dumps({
                "type": "run_started",
                "resume": bool(replayed_ids or replayed_tool_ids),
                "replayed": len(replayed_ids) + len(replayed_tool_ids),
            })})

            async def _stream_agent():
                """Stream the agent until the run completes."""
                async for c in agent.astream(
                    initial_input,
                    config=config,
                    stream_mode=["messages", "events"],
                    subgraphs=True,
                    version="v2",
                ):
                    yield c

            async for chunk in _stream_agent():
                # ── Handle events stream (for namespace → tool_call_id mapping) ──
                # When stream_mode=["messages", "events"], each chunk is a
                # (stream_type, data) tuple. Extract the type first.
                stream_type = None
                if isinstance(chunk, dict) and "type" in chunk and "ns" not in chunk:
                    # This is an events-mode chunk (has 'type' like 'on_chain_start')
                    stream_type = "events"
                elif isinstance(chunk, tuple) and len(chunk) == 2:
                    stream_type, chunk = chunk

                if stream_type == "events":
                    # Process events to build ns_to_tcid mapping.
                    # We look for 'on_chain_start' events from the 'tools' node
                    # that carry the tool_call inputs, linking the namespace to
                    # each task's tool_call_id.
                    if isinstance(chunk, dict):
                        event_type = chunk.get("event", "")
                        event_name = chunk.get("name", "")
                        if event_type == "on_chain_start" and event_name == "tools":
                            event_data = chunk.get("data", {})
                            event_input = event_data.get("input") if isinstance(event_data, dict) else None
                            run_id = chunk.get("run_id", "")
                            tags = chunk.get("tags", [])
                            # The namespace for this event maps to a tools:<task_id>
                            # Attempt to extract tool calls from the input
                            if isinstance(event_input, list):
                                for tc in event_input:
                                    if isinstance(tc, dict) and tc.get("name") == "task":
                                        tc_id = tc.get("id", "")
                                        tc_args = tc.get("args", {})
                                        if isinstance(tc_args, dict) and tc_id:
                                            stype = tc_args.get("subagent_type", "")
                                            if stype:
                                                # Build a mapping: we'll correlate with namespace later
                                                # Store by tool_call_id for now
                                                logger.info("EVENTS: task tool_call id=%s subagent_type=%s", tc_id, stype)
                    continue  # Don't process events as message chunks

                # ── Handle messages stream ──
                ns: tuple = chunk.get("ns", ()) if isinstance(chunk, dict) else ()
                ns_key = "/".join(ns) if ns else ""

                msg_data = chunk.get("data", []) if isinstance(chunk, dict) else chunk
                if isinstance(msg_data, (list, tuple)) and len(msg_data) >= 1:
                    msg_chunk = msg_data[0]
                else:
                    msg_chunk = msg_data

                # A chunk that predates this run is a replay of interrupted
                # work, not new output. Gating it HERE, ahead of the namespace
                # bookkeeping below, is what stops a replayed delegation from
                # re-creating its subagent card in addition to its tool blocks
                # and tokens: a namespace only ever gets registered for a live
                # chunk, so the completion sweep has nothing stale to report.
                if _chunk_already_persisted(msg_chunk, replayed_ids, replayed_tool_ids):
                    continue

                if ns:
                    logger.info("STREAM CHUNK ns=%r key=%r pending=%r", ns, ns_key, pending_delegations)

                if ns_key and ns_key not in active_namespaces:
                    active_namespaces.add(ns_key)
                    subagent_name, task_desc = _pop_delegation(ns, ns_key)
                    subagent_names[ns_key] = subagent_name
                    emit({"event": "message", "data": json.dumps({
                        "type": "subagent_started",
                        "agent": subagent_name,
                        "path": list(ns),
                        "task": task_desc,
                    })})

                if not ns_key and active_namespaces:
                    for completed_ns in list(active_namespaces):
                        if completed_ns not in completed_namespaces:
                            completed_namespaces.add(completed_ns)
                            emit({"event": "message", "data": json.dumps({
                                "type": "subagent_completed",
                                "agent": subagent_names.get(completed_ns, "unknown"),
                                "path": completed_ns.split("/"),
                            })})
                    active_namespaces.clear()

                agent_field = subagent_names.get(ns_key, "") if ns_key else ""

                if (
                    isinstance(msg_chunk, AIMessage)
                    and isinstance(msg_chunk.content, str)
                    and msg_chunk.content
                ):
                    if agent_field != current_agent_field:
                        assistant_content_buf = ""
                        current_agent_field = agent_field
                        think_state["in_think"] = False
                        think_state["buf"] = ""

                    # Split inline <think>…</think> out of the visible answer and
                    # route it to the reasoning channel (Thinking section).
                    visible, think_text = _split_think(msg_chunk.content, think_state)

                    if think_text:
                        assistant_reasoning_buf += think_text
                        rdata = {"type": "reasoning", "content": think_text, "source": "model"}
                        if agent_field:
                            rdata["agent"] = agent_field
                        emit({"event": "message", "data": json.dumps(rdata)})

                    if visible:
                        assistant_content_buf += visible
                        data = {"type": "token", "content": visible}
                        if agent_field:
                            data["agent"] = agent_field
                        emit({"event": "message", "data": json.dumps(data)})

                reasoning_text = _extract_native_reasoning(msg_chunk)
                if reasoning_text:
                    if agent_field != current_agent_field:
                        assistant_content_buf = ""
                        assistant_reasoning_buf = ""
                        current_agent_field = agent_field
                    assistant_reasoning_buf += reasoning_text

                    data = {"type": "reasoning", "content": reasoning_text, "source": "model"}
                    if agent_field:
                        data["agent"] = agent_field
                    emit({"event": "message", "data": json.dumps(data)})

                if hasattr(msg_chunk, "tool_call_chunks") and msg_chunk.tool_call_chunks:
                    for tc in msg_chunk.tool_call_chunks:
                        tc_id = tc.get("id", "")
                        tc_name = tc.get("name", "")
                        tc_args = tc.get("args", "")
                        tc_index = tc.get("index")

                        # A chunk may carry name, args, or BOTH (some gateways
                        # don't split them) — handle each independently; `elif`
                        # here dropped the args of combined chunks.
                        if tc_name:
                            if tc_id:
                                last_named_tcid = tc_id
                                if tc_index is not None:
                                    tc_index_to_id[tc_index] = tc_id
                            if not agent_field and tc_name == "task" and tc_id:
                                task_args_buf[tc_id] = ""
                            if tc_name == "write_todos" and tc_id:
                                todos_buf[tc_id] = ""
                            data = {
                                "type": "tool_call",
                                "tool_name": tc_name,
                                "tool_id": tc_id,
                                "tool_args": "",
                            }
                            if agent_field:
                                data["agent"] = agent_field
                            emit({"event": "message", "data": json.dumps(data)})
                            if tc_id:
                                assistant_tool_calls.setdefault(
                                    tc_id,
                                    {
                                        "toolId": tc_id,
                                        "toolName": tc_name,
                                        "toolArgs": "",
                                        "agent": agent_field or None,
                                    },
                                )

                        if tc_args:
                            eff_id = (
                                tc_id
                                or tc_index_to_id.get(tc_index, "")
                                or last_named_tcid
                            )
                            # Deduplicate accumulated tool args from buggy providers (e.g. vLLM/Qwen)
                            delta_args = tc_args
                            if eff_id:
                                current_buf = ""
                                if eff_id in task_args_buf:
                                    current_buf = task_args_buf[eff_id]
                                elif eff_id in todos_buf:
                                    current_buf = todos_buf[eff_id]
                                
                                if current_buf and tc_args.startswith(current_buf):
                                    delta_args = tc_args[len(current_buf):]

                            if eff_id and eff_id in task_args_buf:
                                task_args_buf[eff_id] += delta_args
                                _try_queue_task(eff_id)
                            if eff_id and eff_id in todos_buf:
                                todos_buf[eff_id] += delta_args
                                items = _parse_write_todos(todos_buf[eff_id])
                                if items is not None:
                                    sig = json.dumps(items, sort_keys=True)
                                    if last_todos_sig.get(agent_field) != sig:
                                        last_todos_sig[agent_field] = sig
                                        emit({"event": "message", "data": json.dumps({
                                            "type": "todos",
                                            "agent": agent_field,
                                            "items": items,
                                        })})
                            data = {
                                "type": "tool_args",
                                "tool_name": tc_name,
                                "tool_id": eff_id,
                                "content": delta_args,
                            }
                            if agent_field:
                                data["agent"] = agent_field
                            emit({"event": "message", "data": json.dumps(data)})
                            if eff_id:
                                rec = assistant_tool_calls.setdefault(
                                    eff_id,
                                    {
                                        "toolId": eff_id,
                                        "toolName": tc_name,
                                        "toolArgs": "",
                                        "agent": agent_field or None,
                                    },
                                )
                                rec["toolArgs"] += delta_args

                if hasattr(msg_chunk, "type") and msg_chunk.type == "tool":
                    tc_name = getattr(msg_chunk, "name", "")
                    tc_id = getattr(msg_chunk, "tool_call_id", "")
                    content_text = (
                        msg_chunk.content if isinstance(msg_chunk.content, str)
                        else str(msg_chunk.content)
                    )
                    data = {
                        "type": "tool_result",
                        "tool_name": tc_name,
                        "tool_id": tc_id,
                        "content": content_text[:_TOOL_RESULT_MAX],
                    }
                    if agent_field:
                        data["agent"] = agent_field
                    emit({"event": "message", "data": json.dumps(data)})
                    if tc_id:
                        rec = assistant_tool_calls.setdefault(
                            tc_id,
                            {
                                "toolId": tc_id,
                                "toolName": tc_name,
                                "toolArgs": "",
                                "agent": agent_field or None,
                            },
                        )
                        rec["result"] = content_text[:_TOOL_RESULT_MAX]

            for completed_ns in list(active_namespaces):
                if completed_ns not in completed_namespaces:
                    emit({"event": "message", "data": json.dumps({
                        "type": "subagent_completed",
                        "agent": subagent_names.get(completed_ns, "unknown"),
                        "path": completed_ns.split("/"),
                    })})

            # Flush any text held back for a partial <think> tag, or an
            # unterminated think block, so nothing is silently dropped.
            leftover = think_state.get("buf", "")
            if leftover:
                think_state["buf"] = ""
                if think_state.get("in_think"):
                    assistant_reasoning_buf += leftover
                    rdata = {"type": "reasoning", "content": leftover, "source": "model"}
                    if current_agent_field:
                        rdata["agent"] = current_agent_field
                    emit({"event": "message", "data": json.dumps(rdata)})
                else:
                    assistant_content_buf += leftover
                    data = {"type": "token", "content": leftover}
                    if current_agent_field:
                        data["agent"] = current_agent_field
                    emit({"event": "message", "data": json.dumps(data)})

            emit({"event": "done", "data": json.dumps({"type": "done"})})

        except BaseException as exc:
            logger.exception("agent_runner failed for thread_id=%s", thread_id)
            try:
                emit({"event": "error", "data": json.dumps({
                    "type": "error", "detail": str(exc),
                })})
            except Exception:
                pass
        finally:
            try:
                await _persist_assistant_message(
                    thread_id,
                    assistant_content_buf,
                    current_agent_field,
                    assistant_reasoning_buf or None,
                    list(assistant_tool_calls.values()) or None,
                )
            except Exception:
                logger.exception(
                    "_persist_assistant_message raised — should be caught inside helper"
                )
            try:
                await _record_run_changes(ws, before_files)
            except Exception:
                logger.exception(
                    "post-run artifact bookkeeping failed for thread_id=%s", thread_id
                )
            # One line per run, because cache behaviour is invisible otherwise:
            # a run that re-bills its whole prefix and a run that is 80% cached
            # look identical in the transcript. Cached tokens are a subset of
            # input, so the ratio is what fraction of input was cache-served.
            try:
                usage = UsageLedger.snapshot(thread_id)
                logger.info(
                    "Run usage thread_id=%s: calls=%d in=%d out=%d cached=%d (%.1f%% cache hit)",
                    thread_id,
                    usage["calls"],
                    usage["input_tokens"],
                    usage["output_tokens"],
                    usage["cached_tokens"],
                    usage["cache_hit_ratio"] * 100,
                )
            except Exception:
                logger.debug("Could not summarise usage for %s", thread_id, exc_info=True)
            # Caveman stats are process-wide (one middleware instance set shared
            # by every agent), so they are logged as a running total next to the
            # per-thread usage line rather than attributed to this run alone.
            try:
                caveman = CavemanStats.snapshot()
                if caveman["results_compacted"]:
                    logger.info(
                        "Caveman read-less totals: results=%d %d→%d chars (%.1f%% saved) %s",
                        caveman["results_compacted"],
                        caveman["chars_before"],
                        caveman["chars_after"],
                        caveman["saved_ratio"] * 100,
                        caveman["by_format"],
                    )
            except Exception:
                logger.debug("Could not summarise caveman stats", exc_info=True)
            ctx.finished = True
            for q in list(ctx.subscribers):
                try:
                    q.put_nowait(None)
                except asyncio.QueueFull:
                    pass
            asyncio.create_task(_cleanup_run_context(thread_id))

    runner_task: asyncio.Task[None] = asyncio.create_task(
        agent_runner(), name=f"agent_runner:{thread_id}"
    )
    _active_runs.add(runner_task)
    runner_task.add_done_callback(_active_runs.discard)
    return ctx

@api.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    request: Request,
    user: CurrentUser = Depends(require_user),
):
    # Before Docker: an unauthorised thread id must never get a container.
    await _owned_conversation(req.thread_id, user)
    agent, backend = await _get_or_create_session(req.thread_id)

    # Make sure the project workspace exists inside this chat's container
    # before the agent starts running shell commands. Without this the
    # agent's first `ls /workspace/project_default/artifacts/` would fail
    # with "no such directory" on every fresh chat. Cheap idempotent check.
    ws = ProjectWorkspace(req.project_id, backend)
    result = await backend.execute_async(
        f"test -d {ws.root} && echo yes || echo no"
    )
    if "no" in result.output:
        ws.init_directories()
        ws.init_project_graph()

    # Re-point /workspace/current at THIS request's project. init_directories
    # only runs on first creation, so a thread that later names a different
    # project would otherwise leave every agent's fixed path on the old one.
    await backend.execute_async(ws.link_current_cmd())

    # Snapshot the workspace inventory BEFORE the agent runs so the post-run
    # bookkeeping (log.md + lineage.json + index.md) can diff against it. On a
    # fresh workspace this is empty, so first-run artifacts log as `produce`.
    before_files = await scan_workspace_files(ws)

    # Invalidate the artifact cache so the frontend's next poll (which
    # fires immediately at the start of streaming) sees fresh data.
    _artifact_cache.pop(f"{req.project_id}:{req.thread_id}", None)

    config = {"configurable": {"thread_id": req.thread_id}}

    # Enrich config with LangSmith metadata
    if is_tracing_enabled():
        config["metadata"] = make_trace_metadata(req.project_id, req.thread_id)
        config["tags"] = ["orchestrator", f"project:{req.project_id}"]

    user_content = _build_user_content(req)

    # Detached runner + multi-subscriber RunContext. The runner is independent
    # of this HTTP response (survives client disconnect); /chat/resume can
    # re-attach. See _spawn_run.
    ctx = _spawn_run(
        thread_id=req.thread_id,
        agent=agent,
        config=config,
        ws=ws,
        before_files=before_files,
        initial_input={"messages": [HumanMessage(content=user_content)]},
    )
    return EventSourceResponse(_event_generator(ctx))

def _wire_event(event: dict[str, Any]) -> dict[str, Any]:
    """Move the run sequence number INTO the JSON payload for the client.

    `_seq` cannot ride as a top-level key: sse-starlette unpacks the dict
    via `ServerSentEvent(**event)` and any unknown kwarg raises TypeError,
    breaking the stream. It used to be stripped here entirely — but that
    left the sequence purely server-side, where it only guards the
    snapshot/queue race inside a single `_event_generator` call.

    The client needs it too. `_event_generator` replays a run's whole
    history to EVERY new subscriber, so a re-attach re-delivers events the
    UI has already applied, and without a sequence there is no way to tell
    a replay from new output — the run's text gets painted twice.

    Nesting it under `data` keeps sse-starlette happy and gives the client
    a monotonic high-water mark to discard against.
    """
    out = {k: v for k, v in event.items() if k != "_seq"}
    seq = event.get("_seq")
    if seq is None:
        return out
    raw = out.get("data")
    if not isinstance(raw, str):
        return out
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return out  # not our JSON envelope — pass through untouched
    if isinstance(payload, dict):
        payload["_seq"] = seq
        out["data"] = json.dumps(payload)
    return out

async def _event_generator(ctx: RunContext):
    """Replay history, then tail live events from a per-subscriber queue.

    Used by BOTH the initial /chat/stream consumer and any later
    /chat/resume re-attacher — same code path, the only difference is
    that the initial caller's snapshot is empty (the runner hasn't
    started emitting yet by the time we subscribe) and the resumer's
    snapshot replays the run-so-far.

    Snapshot-then-tail with `_seq` dedup handles the race where the
    runner emits between our snapshot and the subscribe — see comments
    on `emit()` in chat_stream for why the snapshot+subscribe pair is
    inherently atomic (both are synchronous).
    """
    my_q: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    # Subscribe FIRST so we don't miss events emitted after the
    # snapshot. Synchronous — no await between this and the snapshot
    # line below, so asyncio cannot interleave the runner's emit.
    ctx.subscribers.add(my_q)
    try:
        snapshot = list(ctx.history)
        last_seq = -1
        for event in snapshot:
            seq = event.get("_seq", -1)
            if seq > last_seq:
                last_seq = seq
            yield _wire_event(event)
        # If the run was already finished before we subscribed, the
        # snapshot is the complete event log — nothing more to tail.
        if ctx.finished:
            return
        # Tail live events. The dedup check skips any event that was
        # also in the snapshot (race window between subscribe and
        # snapshot, see emit() docstring).
        while True:
            event = await my_q.get()
            if event is None:
                break
            seq = event.get("_seq", -1)
            if seq <= last_seq:
                continue
            yield _wire_event(event)
    finally:
        ctx.subscribers.discard(my_q)

@api.post("/chat/abort")
async def chat_abort(req: ChatAbortRequest, user: CurrentUser = Depends(require_user)):
    """Abort/cancel an active agent run for the given thread_id."""
    # Not ``required``: abort must reach the same threads that /chat/stream
    # accepted, and thread ids are unguessable client uuids.
    await _owned_conversation(req.thread_id, user)
    thread_id = req.thread_id
    target_name = f"agent_runner:{thread_id}"
    cancelled_count = 0
    for task in list(_active_runs):
        if task.get_name() == target_name:
            task.cancel()
            cancelled_count += 1
    return {
        "status": "ok",
        "detail": f"Aborted {cancelled_count} active agent runs for thread {thread_id}",
    }

@api.get("/chat/resume")
async def chat_resume(
    thread_id: str = Query(..., description="Chat thread to re-attach to"),
    user: CurrentUser = Depends(require_user),
):
    """Re-attach to an in-flight (or recently-finished) agent run.

    Returns an SSE stream that replays the event history accumulated so
    far AND tails live events until the runner finishes. Designed for
    the frontend's switchConversation flow — when the user returns to a
    thread with an active backend run, opening this stream restores the
    in-progress UI (subagent cards, tool calls, streaming tokens) rather
    than showing a blank state until the final persist.

    If no run context exists for `thread_id`, emits a single `done` event
    and closes — the run is over (or was never here), which is exactly what
    `done` means. Callers then fall through to their normal `listMessages`
    path.
    """
    await _owned_conversation(thread_id, user)
    ctx = _run_contexts.get(thread_id)
    if ctx is None:
        # No active run. This used to return a stream that closed with NO
        # terminal event, which silently broke the contract every client
        # callback is keyed to: `onDone` never fired, so nothing that
        # settles run state ran — tool spinners, subagent status, and the
        # sidebar's in-flight marker all stayed as they were. A thread whose
        # run had finished while the user was on another thread would show
        # "WORKING" until a full page reload.
        #
        # "Stream closed" and "run ended" must be the same event, so emit
        # `done` here too. It is idempotent on the client: settling
        # already-settled state is a no-op.
        async def _done_only():
            yield {"event": "done", "data": json.dumps({"type": "done"})}

        return EventSourceResponse(_done_only())
    return EventSourceResponse(_event_generator(ctx))

async def _persist_assistant_message(
    conversation_id: str,
    content: str,
    agent_name: str,
    reasoning: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
) -> None:
    """Write the streamed assistant turn to postgres.

    Idempotency note: callers should invoke this exactly once per agent
    run (success or failure path), not both. The conversation_id is the
    chat thread; `agent_name` is "" for the orchestrator or the subagent
    name. Empty `content` is treated as "nothing to write" — typically
    means the agent emitted only tool calls and no text.
    """
    if not content.strip() and not tool_calls:
        logger.debug(
            "skipping assistant message persist for thread_id=%s — nothing to write",
            conversation_id,
        )
        return

    try:
        async with session_scope() as session:
            row = await conversations_store.append_message(
                session,
                conversation_id,
                role="assistant",
                content=content,
                agent_name=agent_name or None,
                reasoning=reasoning,
                tool_calls=tool_calls,
            )
        if row is None:
            logger.warning(
                "assistant message persist skipped — conversation %s not found",
                conversation_id,
            )
        else:
            logger.info(
                "persisted assistant message for thread_id=%s (%d chars, %d tool calls, agent=%s)",
                conversation_id,
                len(content),
                len(tool_calls or []),
                agent_name or "orchestrator",
            )
    except Exception:
        logger.exception(
            "failed to persist assistant message for thread_id=%s",
            conversation_id,
        )

# ── File upload ────────────────────────────────────────────────────────

@api.post("/upload/{project_id}", response_model=UploadResponse)
async def upload_files(
    project_id: str,
    files: list[UploadFile] = File(...),
    thread_id: str = Query(
        default="default",
        description="Chat thread the file is attached to. Uploads land in the same per-chat container the orchestrator uses for /chat/stream so the agent can read them.",
    ),
    user: CurrentUser = Depends(require_user),
):
    # Route uploads into the chat's own container (harness-{thread_id})
    # rather than the legacy "default" container. The agent invoked by
    # /chat/stream with the same thread_id will see the file at the path
    # returned in this response.
    await _owned_conversation(thread_id, user)
    _agent, backend = await _get_or_create_session(thread_id)
    ws = ProjectWorkspace(project_id, backend)

    # Ensure the project workspace exists
    result = await backend.execute_async(
        f"test -d {ws.root} && echo yes || echo no"
    )
    if "no" in result.output:
        ws.init_directories()
        ws.init_project_graph()

    uploaded: list[dict[str, str]] = []

    for f in files:
        content = await f.read()
        if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"File {f.filename} exceeds {MAX_UPLOAD_SIZE_MB} MB limit",
            )

        container_path = await upload_file_to_container(
            backend=backend,
            thread_id=thread_id,
            filename=f.filename or "unknown",
            content=content,
            target_dir=ws.inputs_dir,
        )
        uploaded.append({
            "path": container_path,
            "original_name": f.filename or "unknown",
        })

    return UploadResponse(thread_id=thread_id, project_id=project_id, files=uploaded)

# ── List uploaded files ────────────────────────────────────────────────

@api.get("/upload/{project_id}")
async def list_uploads(
    project_id: str,
    thread_id: str = Query(default="default", description="Chat thread to list uploads for."),
    user: CurrentUser = Depends(require_user),
):
    await _owned_conversation(thread_id, user)
    _agent, backend = await _get_or_create_session(thread_id)
    ws = ProjectWorkspace(project_id, backend)
    result = await backend.execute_async(
        f"ls -1 {ws.inputs_dir} 2>/dev/null || true"
    )
    files = [line.strip() for line in result.output.strip().split("\n") if line.strip()]
    return {"project_id": project_id, "thread_id": thread_id, "files": files}

# ── Conversation history ────────────────────────────────────────────────

@api.get("/history/{thread_id}")
async def get_history(thread_id: str, user: CurrentUser = Depends(require_user)):
    # The LangGraph checkpoint holds the transcript, so this is a data read,
    # not just a container touch: authorise before waking the sandbox.
    await _owned_conversation(thread_id, user, required=True)
    agent, _backend = await _get_or_create_session(thread_id)
    config = {"configurable": {"thread_id": thread_id}}
    # aget_state: the agent is compiled with an async (AsyncSqliteSaver)
    # checkpointer, which rejects synchronous get_state() calls.
    state = await agent.aget_state(config)
    messages = []
    for msg in state.values.get("messages", []):
        messages.append({
            "role": getattr(msg, "type", getattr(msg, "role", "unknown")),
            "content": getattr(msg, "content", ""),
        })
    return {"thread_id": thread_id, "messages": messages}

# ── Delete session ─────────────────────────────────────────────────────

@api.delete("/session/{thread_id}")
async def delete_session(thread_id: str, user: CurrentUser = Depends(require_user)):
    """Delete a chat session: stop and remove its Docker container."""
    # Destructive, so ownership is required — including for legacy rows whose
    # user_id is NULL, which no account can claim.
    await _owned_conversation(thread_id, user, required=True)
    cleaned_up = _destroy_session(thread_id)
    if cleaned_up:
        return {
            "status": "ok",
            "detail": f"Session {thread_id} destroyed — container stopped and removed",
        }
    return {
        "status": "ok",
        "detail": f"No active session found for {thread_id}",
    }

# ── Custom agents (user-created subagents) ─────────────────────────────
#
# Live propagation: any mutation (create / update / delete) drops every
# cached orchestrator via _invalidate_all_orchestrators(). The next
# message in each thread rebuilds the orchestrator with the fresh
# subagent roster, re-adopting the same Docker container by name so
# workspace state survives. In-flight stream responses keep their old
# agent reference and finish normally.

@api.get("/tools/registry", response_model=ToolRegistryResponse)
async def get_tool_registry_endpoint():
    """Return the tool registry with availability status for each category.

    The frontend uses this to show a checklist of tools the user can
    assign to a custom agent.  ``available`` is ``false`` when the
    underlying tool dependencies are missing at runtime (e.g. `gherkin-official`
    is absent, so the Gherkin gate cannot be instantiated).
    """
    registry = custom_agents_store.get_tool_registry()
    return ToolRegistryResponse(categories=registry)

@api.get("/agents/custom", response_model=CustomAgentListResponse)
async def list_custom_agents_endpoint():
    """List all user-created subagents."""
    return CustomAgentListResponse(agents=custom_agents_store.list_custom_agents())

@api.post("/agents/custom", response_model=CustomAgent)
async def create_custom_agent_endpoint(body: CustomAgentCreate):
    """Create a new user-defined subagent."""
    try:
        created = custom_agents_store.create_custom_agent(
            name=body.name,
            description=body.description,
            system_prompt=body.system_prompt,
            tools=body.tools,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _invalidate_all_orchestrators(f"custom agent created: {created['id']}")
    return created

@api.put("/agents/custom/{agent_id}", response_model=CustomAgent)
async def update_custom_agent_endpoint(agent_id: str, body: CustomAgentUpdate):
    """Update fields of an existing user-defined subagent."""
    try:
        updated = custom_agents_store.update_custom_agent(
            agent_id,
            name=body.name,
            description=body.description,
            system_prompt=body.system_prompt,
            tools=body.tools,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Custom agent {agent_id} not found")
    _invalidate_all_orchestrators(f"custom agent updated: {agent_id}")
    return updated

@api.delete("/agents/custom/{agent_id}")
async def delete_custom_agent_endpoint(agent_id: str):
    """Delete a user-defined subagent."""
    removed = custom_agents_store.delete_custom_agent(agent_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Custom agent {agent_id} not found")
    _invalidate_all_orchestrators(f"custom agent deleted: {agent_id}")
    return {"status": "ok", "detail": f"Custom agent {agent_id} deleted"}

# ── Conversations + messages (Postgres-backed) ──────────────────────────
#
# Replaces the frontend's localStorage:
#   GET    /conversations                       — sidebar listing
#   POST   /conversations                       — new chat
#   PATCH  /conversations/{id}                  — rename
#   DELETE /conversations/{id}                  — drop the row (and its
#                                                  messages); the Docker
#                                                  container is still
#                                                  removed via
#                                                  DELETE /session/{id}.
#   GET    /conversations/{id}/messages         — history hydration
#   POST   /conversations/{id}/messages         — append one message
#   PUT    /conversations/{id}/messages         — bulk replace (used by
#                                                  the localStorage
#                                                  one-time migration)

@api.get("/conversations", response_model=ConversationListResponse)
async def list_conversations_endpoint(user: CurrentUser = Depends(require_user)):
    """Return this user's conversations with their message counts."""
    async with session_scope() as session:
        rows = await conversations_store.list_conversations(session, user.id)
    return ConversationListResponse(
        conversations=[ConversationSummary(**r) for r in rows]
    )

@api.post("/conversations", response_model=ConversationSummary)
async def create_conversation_endpoint(
    body: ConversationCreate, user: CurrentUser = Depends(require_user)
):
    """Create a new conversation row. Idempotency is *not* assumed —
    duplicate ids 409 so the client knows to retry with a fresh uuid."""
    async with session_scope() as session:
        try:
            convo = await conversations_store.create_conversation(
                session,
                conversation_id=body.id,
                user_id=user.id,
                title=body.title,
                project_id=body.project_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        summary = conversations_store.conversation_to_summary_dict(convo, 0)
    return ConversationSummary(**summary)

@api.patch("/conversations/{conversation_id}", response_model=ConversationSummary)
async def update_conversation_endpoint(
    conversation_id: str,
    body: ConversationUpdate,
    user: CurrentUser = Depends(require_user),
):
    """Rename a conversation (currently the only mutable field)."""
    async with session_scope() as session:
        # Authorise before writing: an update on someone else's row must not
        # report anything but "not found".
        _assert_owns(await conversations_store.get_conversation(session, conversation_id), user)
        convo = await conversations_store.update_conversation(
            session, conversation_id, title=body.title
        )
        if convo is None:
            raise HTTPException(
                status_code=404, detail=f"Conversation {conversation_id} not found"
            )
        # Re-fetch the count to keep the response shape consistent with list.
        rows = await conversations_store.list_conversations(session, user.id)
        match = next((r for r in rows if r["id"] == conversation_id), None)
        if match is None:
            # Race-condition guard — extraordinarily unlikely.
            raise HTTPException(
                status_code=404, detail=f"Conversation {conversation_id} vanished"
            )
    return ConversationSummary(**match)

@api.delete("/conversations/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: str, user: CurrentUser = Depends(require_user)
):
    """Drop a conversation and its messages.

    The Docker container survives this call; the existing
    ``DELETE /session/{thread_id}`` endpoint handles container teardown.
    The frontend calls both in sequence on its "delete chat" button.
    """
    async with session_scope() as session:
        _assert_owns(await conversations_store.get_conversation(session, conversation_id), user)
        deleted = await conversations_store.delete_conversation(session, conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Conversation {conversation_id} not found"
        )
    return {"status": "ok", "detail": f"Conversation {conversation_id} deleted"}

@api.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def list_messages_endpoint(
    conversation_id: str, user: CurrentUser = Depends(require_user)
):
    """Return the message history for a conversation."""
    async with session_scope() as session:
        _assert_owns(await conversations_store.get_conversation(session, conversation_id), user)
        rows = await conversations_store.list_messages(session, conversation_id)
    if rows is None:
        raise HTTPException(
            status_code=404, detail=f"Conversation {conversation_id} not found"
        )
    return MessageListResponse(
        conversation_id=conversation_id,
        messages=[MessageOut(**r) for r in rows],
    )

@api.get("/conversations/{conversation_id}/usage")
async def conversation_usage_endpoint(
    conversation_id: str, user: CurrentUser = Depends(require_user)
):
    """Token usage recorded for this thread, including cache hits.

    The point of the endpoint is cached_tokens and cache_hit_ratio. ~96% of
    this pipeline's tokens are input tokens and every call re-sends the same
    ~4k-token prefix, so whether that prefix is served from the provider cache
    is the difference between a chat costing 1x and costing a fraction of it.
    Before this existed the number was unknowable from inside the app.

    Process-local, like the session cache: what this process has served since
    it started, not billing history. Cached tokens are a subset of input
    tokens; cache_hit_ratio is cached/input for the thread.
    """
    # The ledger is process-local and keyed only by id, so the id must be
    # proven to belong to the caller before anything is read out of it.
    await _owned_conversation(conversation_id, user, required=True)
    summary = UsageLedger.snapshot(conversation_id)
    logger.info(
        "Usage for %s: calls=%d in=%d out=%d cached=%d (%.1f%% of input)",
        conversation_id,
        summary["calls"],
        summary["input_tokens"],
        summary["output_tokens"],
        summary["cached_tokens"],
        summary["cache_hit_ratio"] * 100,
    )
    return summary

@api.get("/conversations/{conversation_id}/export")
async def export_conversation_endpoint(
    conversation_id: str, user: CurrentUser = Depends(require_user)
):
    """Export a conversation as a Markdown document.

    The export is a human-readable transcript of the whole thread,
    including every message, the agent's reasoning (thinking), and each
    tool call with its input arguments and output result.  It is returned
    as a downloadable ``.md`` file (``Content-Disposition: attachment``)
    so the user can read, share, or archive the full agent trace.
    """
    from fastapi.responses import Response

    async with session_scope() as session:
        rows = await conversations_store.list_messages(session, conversation_id)
        convo = await conversations_store.get_conversation(session, conversation_id)
    _assert_owns(convo, user)
    if rows is None or convo is None:
        raise HTTPException(
            status_code=404, detail=f"Conversation {conversation_id} not found"
        )

    title = convo.title or "Untitled thread"
    md = _render_conversation_markdown(title, conversation_id, rows)

    filename = f"{title or 'conversation'}.md"
    return Response(
        content=md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": _content_disposition(filename)},
    )

def _render_conversation_markdown(
    title: str, conversation_id: str, rows: list[dict[str, Any]]
) -> str:
    """Render a conversation's messages into a readable Markdown transcript.

    Each message becomes a section with its role, agent, timestamp, and
    content.  Tool calls are rendered as fenced code blocks showing both
    the input arguments and the output result.  Agent reasoning (thinking)
    is rendered in a blockquote so it is visually distinct from the final
    answer.
    """
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- **Thread ID**: `{conversation_id}`")
    lines.append(f"- **Messages**: {len(rows)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, msg in enumerate(rows, start=1):
        role = msg.get("role") or "unknown"
        agent = msg.get("agent_name")
        created = msg.get("created_at") or ""
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning")
        tool_calls = msg.get("tool_calls") or []
        attachments = msg.get("attachments") or []

        role_label = {
            "human": "User",
            "ai": "Assistant",
            "system": "System",
            "tool": "Tool",
        }.get(role, role.capitalize())

        header = f"## {i}. {role_label}"
        meta: list[str] = []
        if agent:
            meta.append(f"**Agent**: {agent}")
        if created:
            meta.append(f"**Time**: {created}")
        if meta:
            header += "  \n" + "  \n".join(meta)
        lines.append(header)
        lines.append("")

        if content:
            lines.append(content.strip())
            lines.append("")

        if reasoning:
            lines.append("> **Reasoning**")
            lines.append(">")
            for rline in reasoning.strip().splitlines():
                lines.append(f"> {rline}")
            lines.append("")

        for tc in tool_calls:
            name = tc.get("toolName") or tc.get("tool_name") or "tool"
            args = tc.get("toolArgs") or tc.get("tool_args") or ""
            result = tc.get("result")
            lines.append(f"### Tool call: `{name}`")
            lines.append("")
            if args:
                lines.append("**Input:**")
                lines.append("")
                lines.append("```json")
                lines.append(_pretty_json(args))
                lines.append("```")
                lines.append("")
            if result is not None:
                lines.append("**Output:**")
                lines.append("")
                lines.append("```")
                lines.append(str(result))
                lines.append("```")
                lines.append("")

        for att in attachments:
            att_name = att.get("name") or att.get("path") or "attachment"
            lines.append(f"*Attachment: `{att_name}`*")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)

def _pretty_json(value: str) -> str:
    """Pretty-print a JSON string; fall back to the raw string on failure."""
    if not value:
        return ""
    try:
        return json.dumps(json.loads(value), indent=2)
    except (json.JSONDecodeError, TypeError):
        return value

@api.post(
    "/conversations/{conversation_id}/messages", response_model=MessageOut
)
async def append_message_endpoint(
    conversation_id: str,
    body: MessageCreate,
    user: CurrentUser = Depends(require_user),
):
    """Append one message to a conversation."""
    async with session_scope() as session:
        _assert_owns(await conversations_store.get_conversation(session, conversation_id), user)
        row = await conversations_store.append_message(
            session,
            conversation_id,
            role=body.role,
            content=body.content,
            agent_name=body.agent_name,
            trace_url=body.trace_url,
            tool_calls=[tc.model_dump() for tc in body.tool_calls] if body.tool_calls else None,
            attachments=[a.model_dump() for a in body.attachments] if body.attachments else None,
        )
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Conversation {conversation_id} not found"
        )
    return MessageOut(**row)

@api.put("/conversations/{conversation_id}/messages")
async def replace_messages_endpoint(
    conversation_id: str, request: Request, user: CurrentUser = Depends(require_user)
):
    """Bulk-replace a conversation's history.

    Used by the frontend's one-time localStorage migration so existing
    chats survive the cutover. Accepts ``{"messages": [{role, content,
    agent_name, trace_url, tool_calls, attachments}, ...]}``. We use a
    raw request body here (rather than a Pydantic schema) to keep this
    forgiving — the migration may carry historical fields the current
    schema doesn't enumerate, and we don't want to drop the message just
    because the shape drifted.
    """
    payload = await request.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
        raise HTTPException(status_code=400, detail="Expected {'messages': [...]} body")

    async with session_scope() as session:
        _assert_owns(await conversations_store.get_conversation(session, conversation_id), user)
        ok = await conversations_store.replace_messages(
            session, conversation_id, payload["messages"]
        )
    if not ok:
        raise HTTPException(
            status_code=404, detail=f"Conversation {conversation_id} not found"
        )
    return {"status": "ok", "detail": f"Replaced messages for {conversation_id}"}

_COMPACTION_SYSTEM_PROMPT = (
    "You are a meticulous assistant summarizing a chat history. Your goal is to "
    "compact/summarize the conversation history between a human and an agent "
    "to reduce tokens while retaining all context.\n"
    "Create a clean, structured summary under the following sections:\n"
    "1. **Core Goal**: What was the primary objective of this thread?\n"
    "2. **Progress & Accomplishments**: What files were created/edited, which "
    "specialist agents were summoned (Ingestion, Architecture, Planning, etc.), "
    "which validators passed or failed, and what results were achieved?\n"
    "3. **Active/Last State**: What is the current status of the project, where "
    "does the codebase or diagram stand, and what is the next step?\n"
    "4. **Decisions & Corrections**: Any key decisions, user feedback, or corrections "
    "made during the chat.\n\n"
    "Keep the summary dense, technical, and complete. Avoid conversational fluff."
)

def _format_history_for_compaction(rows: list[dict[str, Any]]) -> str:
    """Render a conversation for the compaction model, INCLUDING tool evidence.

    This used to emit only ``role``/``agent``/``content``. That silently
    dropped every ``tool_calls`` and ``reasoning`` sidecar, so the model was
    asked to compact the agent's own prose with none of the evidence behind
    it — file reads, validator output, solver results. Whatever the summary
    then asserted became the thread's only ground truth, unfalsifiable and
    uncorrectable. Tool results are what make a summary checkable, so they
    belong in the input.

    Each tool result is capped and the cut is marked, for the same reason
    the shell backend marks its own truncation: an unmarked cut invites the
    model to fill the gap.
    """
    parts: list[str] = []
    for m in rows:
        role = (m.get("role") or "unknown").upper()
        agent = f" (Agent: {m['agent_name']})" if m.get("agent_name") else ""
        parts.append(f"[{role}{agent}]: {m.get('content') or ''}")

        if m.get("reasoning"):
            parts.append(f"  [REASONING]: {_clip(m['reasoning'], 1000)}")

        for tc in m.get("tool_calls") or []:
            name = tc.get("toolName") or tc.get("tool_name") or "tool"
            args = _clip(_pretty_json(tc.get("toolArgs") or tc.get("tool_args") or ""), 600)
            parts.append(f"  [TOOL {name}] input: {args}")
            if tc.get("result") is not None:
                parts.append(f"  [TOOL {name}] output: {_clip(str(tc['result']), 1200)}")

        for att in m.get("attachments") or []:
            parts.append(f"  [ATTACHMENT]: {att.get('name') or att.get('path') or '?'}")

    return "\n\n".join(parts)

def _clip(text: str, limit: int) -> str:
    """Clip to ``limit`` chars, marking the cut so it can't read as complete."""
    if len(text) <= limit:
        return text
    return text[:limit] + f" …[clipped, {len(text) - limit} more chars]"

def _archive_conversation(
    conversation_id: str, title: str, rows: list[dict[str, Any]]
) -> str | None:
    """Write the full pre-compaction transcript to durable storage.

    Compaction deletes the checkpoint tables and truncates the message
    table — both irreversible. Writing the complete transcript first means
    a bad summary is recoverable instead of terminal. Lives next to the
    checkpoint DB, which is on the persistent volume.

    Returns the archive path, or None if archiving failed (the caller
    treats that as a reason NOT to proceed).
    """
    archive_dir = Path(CHECKPOINT_DB_PATH).parent / "compaction_archives"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = archive_dir / f"{conversation_id}-{stamp}.md"
    path.write_text(
        _render_conversation_markdown(title, conversation_id, rows), encoding="utf-8"
    )
    return str(path)

@api.post("/conversations/{conversation_id}/compact")
async def compact_conversation_endpoint(
    conversation_id: str, user: CurrentUser = Depends(require_user)
):
    """Summarize and compact the conversation history to save context tokens.

    Ordering matters and is deliberate: archive, then summarize, and only
    then touch the two stores. Every step that can fail runs before any
    step that destroys data, so a failure leaves the thread intact.
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    from sdlc.services.agent import _build_model, create_orchestrator
    from sdlc.services import agent

    async with session_scope() as session:
        messages = await conversations_store.list_messages(session, conversation_id)
        convo = await conversations_store.get_conversation(session, conversation_id)
    _assert_owns(convo, user)

    if not messages:
        return {"message": "No messages to compact", "summary": ""}

    # ── 1. Archive BEFORE anything destructive ──────────────────────────
    # If this fails we abort: compaction without a recoverable copy trades
    # a full transcript for an unverifiable summary.
    try:
        archive_path = _archive_conversation(
            conversation_id, (convo.title if convo else None) or "Untitled thread", messages
        )
    except Exception as exc:
        logger.exception("Compaction aborted — could not archive %s", conversation_id)
        raise HTTPException(
            status_code=500,
            detail=f"Refusing to compact without an archive: {exc}",
        )

    # ── 2. Summarize (still non-destructive) ────────────────────────────
    history_text = _format_history_for_compaction(messages)
    try:
        model = _build_model()
        response = await model.ainvoke([
            SystemMessage(content=_COMPACTION_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Please compact the following conversation history:\n\n{history_text}"
            ),
        ])
        summary = response.content if isinstance(response.content, str) else str(response.content)
    except Exception as exc:
        logger.exception("Failed to summarize conversation %s", conversation_id)
        raise HTTPException(status_code=500, detail=str(exc))

    compacted_content = (
        "### ── CONVERSATION COMPACTED ──\n"
        "This conversation has been compacted to save context tokens. "
        "The summary below is a LOSSY reconstruction — treat it as a report of "
        "what happened, not as evidence. Re-read the workspace artifacts before "
        "relying on any specific value, and do not invent detail it omits.\n"
        f"The full pre-compaction transcript is archived at `{archive_path}`.\n\n"
        f"{summary}"
    )

    # ── 3. Destructive steps last, once there is something to replace with ──
    try:
        async with session_scope() as session:
            await conversations_store.replace_messages(
                session, conversation_id, [{"role": "system", "content": compacted_content}]
            )

        if agent._checkpoint_conn is not None:
            for table in ["checkpoints", "checkpoint_blobs", "checkpoint_writes", "writes"]:
                try:
                    await agent._checkpoint_conn.execute(
                        f"DELETE FROM {table} WHERE thread_id = ?", (conversation_id,)
                    )
                except Exception:
                    pass
            await agent._checkpoint_conn.commit()

        orch_agent, _ = create_orchestrator(conversation_id)
        await orch_agent.aupdate_state(
            {"configurable": {"thread_id": conversation_id}},
            {"messages": [SystemMessage(content=compacted_content)]},
        )
    except Exception as exc:
        logger.exception(
            "Compaction of %s failed mid-write — transcript archived at %s",
            conversation_id,
            archive_path,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Compaction failed after partial write. Transcript preserved at {archive_path}: {exc}",
        )

    return {
        "message": "Conversation compacted successfully",
        "summary": summary,
        "archive_path": archive_path,
    }

# ── Model settings (base URL / API key / model names) ───────────────────

def _model_settings_response() -> ModelSettingsResponse:
    """Build the GET/PUT response, masking the API key so it never leaks."""
    eff = model_settings.get_effective_settings()
    stored = model_settings.get_stored_settings()
    # Mask any secret values in the `stored` view shown to the UI.
    masked_stored = {
        k: ("••••••" if k in model_settings.SECRET_KEYS else v)
        for k, v in stored.items()
    }
    return ModelSettingsResponse(
        effective=ModelSettings(
            model_provider=eff["model_provider"],
            reasoning_effort=eff["reasoning_effort"],
            base_url=eff["base_url"],
            agent_model=eff["agent_model"],
            vision_model=eff["vision_model"],
            retry_model=eff["retry_model"],
        ),
        api_key_set=bool(eff["api_key"]),
        stored=masked_stored,
    )

@api.get("/settings/model", response_model=ModelSettingsResponse)
async def get_model_settings():
    """Return the resolved model settings (API key masked) plus overrides."""
    return _model_settings_response()

@api.put("/settings/model", response_model=ModelSettingsResponse)
async def update_model_settings(body: ModelSettingsUpdate):
    """Merge a partial update into the model settings JSON store.

    Empty string clears an override (the field falls back to env / default).
    Omitting ``api_key`` leaves the stored key untouched.

    Applies to EXISTING threads too. Orchestrators are cached per thread in
    `_sessions`, and the model is constructed once when that entry is built,
    so without an explicit invalidation a thread keeps whatever model it was
    created with — forever. Changing the model or endpoint in the UI appeared
    to work only on new threads, because only new threads had no cache entry.
    Worse, an old thread would keep calling an endpoint the user had already
    moved away from, and surface that as a provider error they could not act
    on.

    Custom-agent create/update/delete already invalidated for exactly this
    reason; model settings were the omission. Invalidation is cheap: the next
    message rebuilds the orchestrator, and the rebuilt DockerBackend re-adopts
    the same container by name, so workspace state survives untouched.
    """
    try:
        model_settings.update_settings(body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _invalidate_all_orchestrators("model settings updated")
    return _model_settings_response()

# ── MCP servers ──────────────────────────────────────────────────────────
#
# Server definitions live in services/mcp_settings.py (JSON store, masked
# credentials). Tools are loaded by services/mcp.py into a cache that the
# synchronous _build_tools() reads, because create_orchestrator() cannot
# await. Every mutation therefore refreshes the cache AND drops cached
# orchestrators - tools are baked into a subagent spec at build time, so a
# settings change is otherwise invisible until the thread is rebuilt.

_MCP_WARM_TASK: "asyncio.Task[None] | None" = None


async def _warm_mcp_tools() -> None:
    """Seed the preset catalog, then load every enabled server. Never fatal."""
    try:
        # Seeds once (the store records that it ran) so a fresh database gets
        # the phase-mapped catalog without resurrecting deleted servers later.
        mcp_settings.seed_presets()
        await mcp_client.refresh()
    except Exception as exc:  # noqa: BLE001 - MCP must not block boot
        logger.warning("MCP warm-up failed: %s", exc)


async def _reload_mcp(reason: str) -> None:
    """Reconnect enabled servers, then invalidate cached orchestrators."""
    try:
        await mcp_client.refresh()
    except Exception as exc:  # noqa: BLE001 - a bad server must not fail the write
        logger.warning("MCP refresh failed: %s", exc)
    _invalidate_all_orchestrators(reason)


@api.get("/mcp/servers", response_model=McpServersResponse)
async def list_mcp_servers() -> McpServersResponse:
    """Stored MCP servers, adapter availability, and last load status."""
    return McpServersResponse(
        servers=[McpServerOut(**server) for server in mcp_settings.public_servers()],
        adapter_available=mcp_client.available(),
        adapter_error=mcp_client.adapter_error(),
        status=[McpServerStatus(**entry) for entry in mcp_client.status().values()],
    )


@api.post("/mcp/servers", response_model=McpServerOut)
async def create_mcp_server(body: McpServerCreate) -> McpServerOut:
    """Add a server. Credential values are stored but never echoed back."""
    try:
        server = mcp_settings.create_server(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _reload_mcp(f"mcp server created: {server['id']}")
    created = mcp_settings.public_server(server["id"])
    assert created is not None  # just written
    return McpServerOut(**created)


@api.put("/mcp/servers/{server_id}", response_model=McpServerOut)
async def update_mcp_server(server_id: str, body: McpServerUpdate) -> McpServerOut:
    """Patch a server. Omitting env/headers keeps the stored credentials."""
    try:
        mcp_settings.update_server(server_id, body.model_dump(exclude_unset=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="MCP server not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _reload_mcp(f"mcp server updated: {server_id}")
    updated = mcp_settings.public_server(server_id)
    assert updated is not None  # just written
    return McpServerOut(**updated)


@api.delete("/mcp/servers/{server_id}")
async def delete_mcp_server(server_id: str) -> dict[str, bool]:
    if not mcp_settings.delete_server(server_id):
        raise HTTPException(status_code=404, detail="MCP server not found")
    await _reload_mcp(f"mcp server deleted: {server_id}")
    return {"deleted": True}


@api.post("/mcp/servers/presets", response_model=list[McpServerOut])
async def restore_mcp_presets() -> list[McpServerOut]:
    """Re-add catalog entries the user deleted; existing servers are untouched."""
    added = mcp_settings.seed_presets(force=True)
    await _reload_mcp(f"mcp presets restored: {len(added)} added")
    return [McpServerOut(**mcp_settings.public_server(server["id"])) for server in added]


@api.post("/mcp/servers/{server_id}/test", response_model=McpTestResponse)
async def test_mcp_server(server_id: str) -> McpTestResponse:
    """Connect once and report exposed tools - backs the panel's Test button."""
    server = mcp_settings.get_server(server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return McpTestResponse(**await mcp_client.test_server(server))


@api.post("/mcp/servers/{server_id}/oauth")
async def start_mcp_oauth(server_id: str) -> dict[str, Any]:
    server = mcp_settings.get_server(server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="MCP server not found")
    if not mcp_client.available():
        raise HTTPException(status_code=503, detail="MCP adapter is unavailable")
    from sdlc.services import mcp_oauth
    try:
        url = await mcp_oauth.start(server, _reload_mcp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"authorization_url": url, **mcp_oauth.status(server_id)}


@api.get("/mcp/servers/{server_id}/oauth")
async def mcp_oauth_status(server_id: str) -> dict[str, Any]:
    from sdlc.services import mcp_oauth

    if mcp_settings.get_server(server_id) is None:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return mcp_oauth.status(server_id)


@api.get("/mcp/oauth/callback")
async def mcp_oauth_callback(state: str, code: str | None = None, error: str | None = None):
    from fastapi.responses import HTMLResponse
    from sdlc.services import mcp_oauth

    try:
        complete = await mcp_oauth.finish(state, code, error)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    message = "Connected. You can close this window." if complete else "Connection failed. Close this window and try again in MCP settings."
    return HTMLResponse(f"<!doctype html><title>MCP connection</title><p>{message}</p>",
                        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@api.post("/mcp/servers/{server_id}/oauth/cancel")
async def cancel_mcp_oauth(server_id: str) -> dict[str, bool]:
    from sdlc.services import mcp_oauth

    await mcp_oauth.cancel(server_id)
    return {"cancelled": True}


# ── Skills management ───────────────────────────────────────────────────

SKILLS_HOST_DIR = Path(__file__).resolve().parent.parent / "skills"

@api.get("/skills", response_model=list[SkillInfo])
async def list_skills() -> list[SkillInfo]:
    """List all available skills inside the skills directory."""
    if not SKILLS_HOST_DIR.exists() or not SKILLS_HOST_DIR.is_dir():
        return []
    
    skills = []
    for item in sorted(SKILLS_HOST_DIR.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            has_skill = (item / "SKILL.md").exists()
            has_learned = (item / "LEARNED.md").exists()
            skills.append(
                SkillInfo(
                    name=item.name,
                    has_skill=has_skill,
                    has_learned=has_learned
                )
            )
    return skills

@api.get("/skills/{skill_name}", response_model=SkillDetailsResponse)
async def get_skill_details(skill_name: str) -> SkillDetailsResponse:
    """Return the contents of SKILL.md and LEARNED.md for a given skill."""
    if ".." in skill_name or "/" in skill_name or "\\" in skill_name:
        raise HTTPException(status_code=400, detail="Invalid skill name")

    skill_dir = SKILLS_HOST_DIR / skill_name
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise HTTPException(
            status_code=404, detail=f"Skill '{skill_name}' not found"
        )
    
    skill_file = skill_dir / "SKILL.md"
    learned_file = skill_dir / "LEARNED.md"
    
    skill_content = ""
    if skill_file.exists() and skill_file.is_file():
        skill_content = skill_file.read_text(encoding="utf-8")
        
    learned_content = ""
    if learned_file.exists() and learned_file.is_file():
        learned_content = learned_file.read_text(encoding="utf-8")
        
    return SkillDetailsResponse(
        name=skill_name,
        skill_content=skill_content,
        learned_content=learned_content
    )

@api.put("/skills/{skill_name}", response_model=SkillDetailsResponse)
async def update_skill_details(skill_name: str, body: SkillUpdateRequest) -> SkillDetailsResponse:
    """Update SKILL.md and/or LEARNED.md contents for a given skill."""
    if ".." in skill_name or "/" in skill_name or "\\" in skill_name:
        raise HTTPException(status_code=400, detail="Invalid skill name")

    skill_dir = SKILLS_HOST_DIR / skill_name
    if not skill_dir.exists() or not skill_dir.is_dir():
        try:
            skill_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create skill directory: {str(e)}"
            )
            
    skill_file = skill_dir / "SKILL.md"
    learned_file = skill_dir / "LEARNED.md"
    
    if body.skill_content is not None:
        try:
            skill_file.write_text(body.skill_content, encoding="utf-8")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to write SKILL.md: {str(e)}"
            )
            
    if body.learned_content is not None:
        try:
            learned_file.write_text(body.learned_content, encoding="utf-8")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to write LEARNED.md: {str(e)}"
            )
            
    skill_content = ""
    if skill_file.exists() and skill_file.is_file():
        skill_content = skill_file.read_text(encoding="utf-8")
        
    learned_content = ""
    if learned_file.exists() and learned_file.is_file():
        learned_content = learned_file.read_text(encoding="utf-8")
        
    return SkillDetailsResponse(
        name=skill_name,
        skill_content=skill_content,
        learned_content=learned_content
    )

# ── Route registration ─────────────────────────────────────────────────
# Includes the authenticated router. Must run after every ``@api.*``
# decorator above, i.e. at the end of the module.
app.include_router(api)

# ── Frontend static files ──────────────────────────────────────────────

if _FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
else:
    logger.warning("Frontend directory not found at %s — skipping static mount", _FRONTEND_DIR)

# ── Entry-point ─────────────────────────────────────────────────────────

def main():
    """Run the uvicorn server."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    uvicorn.run(
        "sdlc.api.app:app",
        host=HOST,
        port=PORT,
        reload=False,
    )

if __name__ == "__main__":
    main()
