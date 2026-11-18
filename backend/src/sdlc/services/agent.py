"""SDLC Orchestrator agent factory.

Creates a compiled LangGraph agent with seven specialist subagents wired
through a Docker sandbox backend.  Subagent definitions, the orchestrator
prompt, and tool loading live in ``sdlc.services.subagents``.
"""

from __future__ import annotations

import contextvars
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiosqlite
import langchain.agents
import langchain.agents.factory
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
from deepagents.middleware.subagents import SubAgentMiddleware
from langchain.agents.middleware import ModelCallLimitMiddleware, ModelRetryMiddleware
from langchain_openai import ChatOpenAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.memory import InMemoryStore

from sdlc.sandbox.docker_backend import DockerBackend
from sdlc.core.config import (
    CHECKPOINT_DB_PATH,
    DOCKER_CLIENT_TIMEOUT,
    DOCKER_IMAGE,
    DOCKER_KEEP_ALIVE,
    DOCKER_NETWORK,
    DOCKER_POOL_SIZE,
    DOCKER_SANDBOX_CPUS,
    DOCKER_SANDBOX_MEM_LIMIT,
    DOCKER_SANDBOX_PIDS_LIMIT,
    DOCKER_SANDBOX_USER,
    DOCKER_WORKDIR,
    PROMPT_CACHE_KEY,
    SDLC_MAX_INPUT_TOKENS,
    SDLC_MAX_LLM_INVOCATIONS,
    MODEL_NAME,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_TEMPERATURE,
)
from sdlc.services.subagents import (
    ALL_SUBAGENTS,
    ORCHESTRATOR_PROMPT,
    SKILLS_HOST_DIR,
    _build_orchestrator_tools,
    _build_tools,
    attach_tools,
)
from sdlc.services.custom_agents import custom_agents_as_subagent_specs
from sdlc.services.caveman import (
    CavemanStats,
    caveman_middleware,
    recovery_tools,
)
from sdlc.services.hitl import ShellGuardMiddleware
from sdlc.services.usage import UsageRecordingHandler

logger = logging.getLogger(__name__)

# Root for deepagents' own context offload, INSIDE the thread's sandbox.
#
# Both offload families derive their prefix from the composite backend's
# `artifacts_root`:
#   * FilesystemMiddleware writes any tool result over its token limit to
#     `<root>/large_tool_results/<tool_call_id>` and leaves a stub behind.
#   * SummarizationMiddleware appends evicted turns to
#     `<root>/conversation_history/<session_id>.md` and names that path in the
#     summary it leaves in context.
#
# Derived from DOCKER_WORKDIR rather than hardcoded so it cannot drift from the
# workdir the sandbox is actually started with: DOCKER_WORKDIR is also what
# create_orchestrator passes to DockerBackend.
CONTEXT_OFFLOAD_DIR = f"{DOCKER_WORKDIR.rstrip('/')}/.context"


# Context variables to hold the active checkpointer and store during deep agent compilation.
_active_checkpointer_cv = contextvars.ContextVar("active_checkpointer", default=None)
_active_store_cv = contextvars.ContextVar("active_store", default=None)


def _patch_subagent_middleware() -> None:
    """Monkey-patch SubAgentMiddleware._get_subagents to inject checkpointer & store.

    DeepAgents >=0.6.10 removed the internal ``_get_subagents`` hook that earlier
    versions used to pass checkpointer/store into subagents. This patch only
    activates when the hook exists; newer versions pass these values directly.
    """
    if not hasattr(SubAgentMiddleware, "_get_subagents"):
        return

    original_get_subagents = SubAgentMiddleware._get_subagents

    def _patched_get_subagents(self):  # type: ignore[misc]
        """Wraps ``create_agent`` to inject the current checkpointer and store."""
        original_create_agent = langchain.agents.factory.create_agent

        def _create_agent_with_context(*args, **kwargs):
            ckptr = _active_checkpointer_cv.get()
            store = _active_store_cv.get()
            if ckptr is not None and "checkpointer" not in kwargs:
                kwargs["checkpointer"] = ckptr
            if store is not None and "store" not in kwargs:
                kwargs["store"] = store
            return original_create_agent(*args, **kwargs)

        langchain.agents.factory.create_agent = _create_agent_with_context
        langchain.agents.create_agent = _create_agent_with_context
        try:
            return original_get_subagents(self)
        finally:
            langchain.agents.factory.create_agent = original_create_agent
            langchain.agents.create_agent = original_create_agent

    SubAgentMiddleware._get_subagents = _patched_get_subagents


_patch_subagent_middleware()


# ── Model factory ────────────────────────────────────────────────────────


# Hosts where prompt_cache_key is a documented request parameter. Everywhere
# else the field is either meaningless or rejected, so _prompt_cache_key will
# not guess: "auto" opts in only here, and a gateway the operator knows accepts
# it can be enabled explicitly with PROMPT_CACHE_KEY=on.
_OPENAI_HOSTS = frozenset({"api.openai.com"})


def _prompt_cache_key(settings: dict[str, str], thread_id: str | None) -> str | None:
    """Stable per-thread routing key for the provider's prompt cache.

    The cacheable unit is the request *prefix* — the static system prompt plus
    the tool schemas, ~4k tokens on every orchestrator call. Providers cache it
    automatically once the prefix repeats, but OpenAI also routes on
    prompt_cache_key: requests carrying the same key are steered to the same
    cache shard, which is what keeps a long chat hitting rather than missing.

    Returns None when it must not be sent. Unknown OpenAI-compatible gateways
    are the reason for the "auto" mode: sending an undocumented body field to a
    server that validates strictly turns every chat into a 400.
    """
    mode = (PROMPT_CACHE_KEY or "auto").strip().lower()
    if not thread_id or mode in ("", "off", "0", "false", "none"):
        return None
    if mode in ("on", "1", "true", "always"):
        return thread_id
    host = urlparse(settings.get("base_url") or "").hostname or ""
    return thread_id if host in _OPENAI_HOSTS else None


def _build_model(thread_id: str | None = None) -> ChatOpenAI | ChatNVIDIA:
    """Construct a model from the runtime model settings.

    Reads provider / base URL / API key / agent model fresh from the model-settings
    store (UI override > env > default) so changes made in the Settings
    panel take effect for newly created chat sessions without a restart.
    Temperature stays config-driven.

    *thread_id* does two things. It attaches the usage ledger, so every model
    call this instance makes is counted (deepagents shares one model object
    with the orchestrator and all subagents, so this is the whole run), and it
    becomes the provider's prompt-cache routing key — one cache shard per chat
    rather than one per process.
    """
    import os
    from sdlc.services import model_settings

    settings = model_settings.get_effective_settings()
    provider = settings.get("model_provider", "openai")

    callbacks: list[Any] = []
    if thread_id:
        callbacks.append(UsageRecordingHandler(thread_id))
    cache_key = _prompt_cache_key(settings, thread_id)

    if provider == "nvidia":
        agent_model = settings["agent_model"]
        if agent_model == "mistralai/Mistral-Large-3.1-128B":
            agent_model = "minimaxai/minimax-m3"

        api_key = settings.get("api_key") or os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY", "")

        kwargs: dict[str, Any] = {
            "model": agent_model,
            "api_key": api_key,
            "temperature": 1.0,
            "top_p": 0.95,
            "max_completion_tokens": 8192,
        }
        # If user explicitly overrode base_url and it is not the default OpenAI base URL, pass it
        if settings.get("base_url") and settings["base_url"] != "https://hub.nhr.fau.de/api/llmgw/v1":
            kwargs["base_url"] = settings["base_url"]

        reasoning_effort = settings.get("reasoning_effort", "")
        if reasoning_effort in ("low", "medium", "high"):
            kwargs["reasoning_effort"] = reasoning_effort
        if callbacks:
            kwargs["callbacks"] = callbacks

        model = ChatNVIDIA(**kwargs)
        logger.info(
            "Model created: ChatNVIDIA(model=%s, reasoning_effort=%s)",
            agent_model,
            kwargs.get("reasoning_effort", "default"),
        )
    else:
        kwargs: dict[str, Any] = {
            "model": settings["agent_model"],
            "temperature": OPENAI_TEMPERATURE,
            "base_url": settings["base_url"],
            # Disable the stream chunk timeout — subagents and tool execution
            # can take minutes between model tokens without being dead.
            "stream_chunk_timeout": None,
        }
        if settings["api_key"]:
            kwargs["api_key"] = settings["api_key"]

        reasoning_effort = settings.get("reasoning_effort", "")
        if reasoning_effort in ("low", "medium", "high"):
            kwargs["reasoning_effort"] = reasoning_effort
        if callbacks:
            kwargs["callbacks"] = callbacks
        if cache_key:
            # Goes into the request body, not the URL: OpenAI reads it as the
            # cache-routing hint for this conversation.
            kwargs["extra_body"] = {"prompt_cache_key": cache_key}

        model = ChatOpenAI(**kwargs)

        # Declare the model's context window so deepagents' auto-added
        # SummarizationMiddleware uses fraction-based triggers (0.85/0.10)
        # rather than its fixed ("tokens", 170000) fallback.
        #
        # Deliberately NOT hardcoded. This was 1_048_576 — verified correct
        # for deepseek-v4-flash on Ollama, and silently wrong the moment
        # OPENAI_BASE_URL pointed somewhere else. A window declared larger
        # than the endpoint's real one is worse than declaring none: the
        # trigger sits above the true limit, so summarization never fires
        # and the provider hard-errors on overflow instead.
        #
        # Unset means "unknown", which falls through to the conservative
        # fixed trigger. See SDLC_MAX_INPUT_TOKENS in core/config.py.
        if not model.profile and SDLC_MAX_INPUT_TOKENS > 0:
            model.profile = {"max_input_tokens": SDLC_MAX_INPUT_TOKENS}
        logger.info(
            "Model created: ChatOpenAI(model=%s, base_url=%s, reasoning_effort=%s,"
            " profile=%s, prompt_cache_key=%s)",
            settings["agent_model"],
            settings["base_url"],
            kwargs.get("reasoning_effort", "default"),
            model.profile,
            cache_key or "not sent",
        )

    return model


# ── Agent factory ───────────────────────────────────────────────────────

# Persistent checkpointer: stores per-thread conversation memory in a
# SQLite file so chats reopened after a server restart resume with full
# history. deepagents drives the graph asynchronously, so we use
# AsyncSqliteSaver backed by aiosqlite. Construction requires await, so
# init_checkpointer() is called from the FastAPI lifespan startup.
_checkpoint_conn: aiosqlite.Connection | None = None
_checkpointer: AsyncSqliteSaver | None = None

# Cross-agent shared memory store. Ephemeral by design: subagents use it
# for scratch-pad style memory that does not need to outlive the process.
_langgraph_store = InMemoryStore()


async def init_checkpointer() -> None:
    """Open the aiosqlite connection and create the checkpoint schema.

    Idempotent: safe to call multiple times. Must be awaited before any
    call to create_orchestrator().
    """
    global _checkpoint_conn, _checkpointer
    if _checkpointer is not None:
        return
    Path(CHECKPOINT_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    _checkpoint_conn = await aiosqlite.connect(CHECKPOINT_DB_PATH)
    _checkpointer = AsyncSqliteSaver(_checkpoint_conn)
    await _checkpointer.setup()
    logger.info("Checkpoint DB ready at %s", CHECKPOINT_DB_PATH)


async def close_checkpointer() -> None:
    """Close the aiosqlite connection. Called from the lifespan shutdown."""
    global _checkpoint_conn, _checkpointer
    if _checkpoint_conn is not None:
        await _checkpoint_conn.close()
        _checkpoint_conn = None
        _checkpointer = None
        logger.info("Checkpoint DB connection closed")


# Container names must match [a-zA-Z0-9][a-zA-Z0-9_.-]+. The frontend uses
# crypto.randomUUID() which is already safe; this is just defensive in case
# a custom thread_id sneaks through.
_UNSAFE_NAME = re.compile(r"[^a-zA-Z0-9_.-]")


def _safe_name(thread_id: str) -> str:
    """Sanitise a thread_id into a Docker-safe container name fragment."""
    sanitised = _UNSAFE_NAME.sub("-", thread_id).strip("-_.") or "default"
    return sanitised[:200]  # Docker hard cap is well above this


def container_name_for(thread_id: str) -> str:
    """Return the deterministic Docker container name for *thread_id*.

    Single source of truth — used by create_orchestrator() and by the
    delete handler so a chat's container can be found on disk even
    when no live session exists for it in memory.
    """
    return f"harness-{_safe_name(thread_id)}"


def create_orchestrator(thread_id: str) -> tuple[Any, DockerBackend]:
    """Create the orchestrator agent and its Docker backend for *thread_id*.

    Each chat thread owns its own Docker container, named
    ``harness-<thread_id>``. The deterministic name lets the backend
    reattach to a previously-stopped container after a server restart
    (see DockerBackend._ensure_container).

    Returns:
        (compiled_agent, docker_backend) — the compiled LangGraph agent
        and the DockerBackend so the caller can access the container ID,
        upload files, etc.
    """
    if _checkpointer is None:
        msg = (
            "Checkpoint DB not initialised — init_checkpointer() must be "
            "awaited from the FastAPI lifespan startup before any chat."
        )
        raise RuntimeError(msg)

    model = _build_model(thread_id)

    # Lazily instantiate domain tools (skips gracefully if deps are missing)
    tools_map = _build_tools()

    # Attach tools to subagent specs that need them
    subagents = attach_tools(ALL_SUBAGENTS, tools_map)

    # Append user-created subagents from custom_agents.json. Each inherits the
    # default deep-agent toolset plus any domain tools resolved from its
    # ``tools`` field (see custom_agents_as_subagent_specs). Mutations
    # invalidate every cached orchestrator (app.py::_invalidate_all_orchestrators),
    # so changes reach existing chats on their next message, not just new ones.
    custom_specs = custom_agents_as_subagent_specs()
    if custom_specs:
        subagents = list(subagents) + custom_specs
        logger.info(
            "Merged %d custom subagent(s) into orchestrator for thread_id=%s: %s",
            len(custom_specs),
            thread_id,
            [s["name"] for s in custom_specs],
        )

    container_name = container_name_for(thread_id)
    docker_backend = DockerBackend(
        image=DOCKER_IMAGE,
        container_name=container_name,
        workdir=DOCKER_WORKDIR,
        keep_alive=DOCKER_KEEP_ALIVE,
        auto_create=True,
        network=DOCKER_NETWORK,
        max_pool_size=DOCKER_POOL_SIZE,
        client_timeout=DOCKER_CLIENT_TIMEOUT,
        # Isolation floor for the per-chat sandbox — see docker_backend.py's
        # module constants. Ceilings matter: without them one chat's runaway
        # script OOMs the host and takes every other chat's backend with it.
        sandbox_user=DOCKER_SANDBOX_USER,
        mem_limit=DOCKER_SANDBOX_MEM_LIMIT,
        nano_cpus=int(DOCKER_SANDBOX_CPUS * 1_000_000_000),
        pids_limit=DOCKER_SANDBOX_PIDS_LIMIT,
    )

    # Ensure base directories exist (also triggers container creation /
    # reattach if a previous one already exists with this name).
    #
    # The offload directories are created up front rather than left to the
    # middleware: an offload write happens mid-run, and a missing parent turns a
    # recoverable eviction into a failed tool call. Creating them is idempotent,
    # so this is also the migration path for containers that predate the root.
    docker_backend.execute(
        "mkdir -p /workspace/uploads /workspace/output"
        f" {CONTEXT_OFFLOAD_DIR}/large_tool_results"
        f" {CONTEXT_OFFLOAD_DIR}/conversation_history"
    )

    # CompositeBackend: default workspace in container (also where the context
    # offload lands, via artifacts_root below), memories cross-thread, skills
    # mounted from the host filesystem.
    backend = CompositeBackend(
        default=docker_backend,
        routes={
            # deepagents >= 0.6 requires an explicit namespace factory for
            # StoreBackend; a fixed tuple keeps memories shared across threads.
            "/memories/": StoreBackend(
                store=_langgraph_store,
                namespace=lambda _rt: ("sdlc", "memories"),
            ),
            "/skills/": FilesystemBackend(
                root_dir=str(SKILLS_HOST_DIR),
                virtual_mode=True,
            ),
        },
        # Root for deepagents' own context offload (see CONTEXT_OFFLOAD_DIR).
        #
        # Deliberately INSIDE the thread's sandbox, not on the backend volume
        # where an earlier revision routed it. Two reasons:
        #
        #   * co-location. This is context the harness shed, so it belongs
        #     beside the artifacts it was derived from, reachable with the same
        #     `ls` / `cat` / `read_file` tools the agent already uses for
        #     everything else. The old `/conversation_history/` route was a
        #     virtual mount: readable through the agent's file tools but
        #     invisible to shell, so the "full history at ..." pointer that a
        #     summary embeds could not simply be cat-ed.
        #   * the durability argument for routing it out no longer holds.
        #     Containers are named deterministically (`harness-<thread_id>`),
        #     are stopped-not-removed on backend shutdown
        #     (app.py::_stop_session_keep_container) and re-adopted on restart
        #     (DockerBackend._ensure_container), so the path survives the
        #     backend restart that reasoning was written about. A container is
        #     removed only when the chat itself is deleted.
        #
        # NOT `<workdir>/current/.context`: `current` is a symlink to the real
        # project directory (ProjectWorkspace.link_current_cmd), so writes
        # through it would be picked up by scan_workspace_files and logged in
        # index.md / log.md as produced artifacts. `/.context` is a sibling of
        # the project directory, which that scan deliberately never reaches.
        artifacts_root=CONTEXT_OFFLOAD_DIR,
    )

    # Orchestrator-level tools (web search etc.) — attached only to the
    # top-level agent. Subagents stay deterministic on their structured
    # artifacts; the orchestrator is the only place where external lookup
    # is appropriate.
    orchestrator_tools = [*_build_orchestrator_tools(), *recovery_tools()]

    token_checkpointer = _active_checkpointer_cv.set(_checkpointer)  # type: ignore
    token_store = _active_store_cv.set(_langgraph_store)  # type: ignore
    try:
        middleware: list[Any] = [
            ModelRetryMiddleware(
                max_retries=3,
                backoff_factor=2.0,
                initial_delay=1.0,
            ),
            ShellGuardMiddleware(),
            # Caveman "read less", at the one point every tool result crosses:
            # the orchestrator's own calls (notably task() subagent reports,
            # which are the largest payloads in the run) and, via
            # _retry_middleware(), all seven subagents' calls too.
            *caveman_middleware(),
        ]
        # R2 (cost-eval feasibility): bound worst-case LLM invocations per
        # run. The 20-trial CostEvals batch peaked at 88 model calls (median
        # 71); the subagent dispatch count is constant at 7, so the cost tail
        # is orchestrator loop iterations. Env-gated (off on the live chat
        # path; set SDLC_MAX_LLM_INVOCATIONS for eval runs). A gentle ceiling
        # above the observed max makes the orchestrator wrap up rather than
        # hard-error mid-run.
        if SDLC_MAX_LLM_INVOCATIONS > 0:
            middleware.insert(0, ModelCallLimitMiddleware(
                run_limit=SDLC_MAX_LLM_INVOCATIONS,
                exit_behavior="end",
            ))
            logger.info(
                "ModelCallLimitMiddleware armed: max %d LLM invocations per run (R2)",
                SDLC_MAX_LLM_INVOCATIONS,
            )

        agent = create_deep_agent(
            model=model,
            backend=backend,
            system_prompt=ORCHESTRATOR_PROMPT,
            tools=orchestrator_tools,
            subagents=subagents,  # type: ignore
            store=_langgraph_store,
            checkpointer=_checkpointer,
            # Deterministic safety guard: hard-block destructive shell commands.
            middleware=middleware,
        )
    finally:
        _active_checkpointer_cv.reset(token_checkpointer)
        _active_store_cv.reset(token_store)

    logger.info(
        "Orchestrator agent created for thread_id=%s (model=%s, docker=%s, container=%s)",
        thread_id,
        MODEL_NAME,
        DOCKER_IMAGE,
        container_name,
    )
    return agent, docker_backend
