"""Application configuration loaded from environment variables.

Also loads a ``.env`` file from the backend directory if present.
"""

from __future__ import annotations

import os
from pathlib import Path

# config.py lives at: backend/src/sdlc/core/config.py
# .env lives at: backend/.env — go up 4 parents to reach backend/.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Load .env from backend/ before reading any env vars.  override=True so
# .env values take precedence over shell env vars — this ensures the
# NHR gateway API key is used, not a system-level OpenAI key.
_dotenv_path = _BACKEND_ROOT / ".env"
if _dotenv_path.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(_dotenv_path, override=True)
    except ImportError:
        pass  # python-dotenv not installed — rely on shell env vars

# ── Model (OpenAI / ChatOpenAI) ───────────────────────────────────────
MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "openai")
MODEL_NAME: str = os.getenv("AGENT_MODEL", "mistralai/Mistral-Large-3.1-128B")
RETRY_MODEL: str = os.getenv("RETRY_MODEL", "")
REASONING_EFFORT: str = os.getenv("REASONING_EFFORT", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv(
    "OPENAI_BASE_URL", "https://hub.nhr.fau.de/api/llmgw/v1"
)  # NHR FAU endpoint by default
OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

# ── Prompt caching ─────────────────────────────────────────────────────
# The cacheable unit is the request prefix: the static orchestrator system
# prompt (~3.9k tokens) plus the tool schemas, re-sent on every model call.
# ~96% of this pipeline's tokens are input tokens, so that prefix is the
# whole lever.
#
# Providers cache it on their own once the prefix repeats; this setting only
# controls the routing hint that keeps a conversation on the same cache
# shard. "auto" sends it to api.openai.com, where the parameter is
# documented, and nowhere else — an unknown OpenAI-compatible gateway may
# reject an undocumented body field, which would fail every chat rather than
# slowly. Use "on" for a gateway known to accept prompt_cache_key, "off" to
# never send it.
PROMPT_CACHE_KEY: str = os.getenv("PROMPT_CACHE_KEY", "auto")

# ── Caveman: read less ──────────────────────────────────────────────────
# Native port of the caveman "read less" idea (services/caveman.py): tool
# results are compacted deterministically before they enter the model
# context, the exact bytes are kept, and caveman_retrieve pages them back.
#
# "read" (default) compacts tool results; "off" passes everything through.
# This never touches artifacts, prompts or tool inputs — only results, on
# the way in. Set CAVEMAN_MODE=off to A/B the effect on artifact quality,
# and watch the per-run "Run usage" line for the char saving either way.
CAVEMAN_MODE: str = os.getenv("CAVEMAN_MODE", "read")
# Below this size nothing is compacted: the footer and a possible retrieve
# round-trip cost more than the saving.
CAVEMAN_MIN_CHARS: int = int(os.getenv("CAVEMAN_MIN_CHARS", "2000"))
# Content-addressed store of originals. Backend-local: never in the sandbox,
# never committed (backend/data/ is ignored).
CAVEMAN_STORE_DIR: str = os.getenv(
    "CAVEMAN_STORE_DIR", str(_BACKEND_ROOT / "data" / "caveman")
)
# Cap on stored originals. A long-lived backend would otherwise accumulate one
# file per unique tool result forever; oldest-first eviction keeps the recent
# retrieval targets, which are the ones a running conversation still needs.
CAVEMAN_STORE_MAX: int = int(os.getenv("CAVEMAN_STORE_MAX", "500"))

# ── Product identity ───────────────────────────────────────────────────
# The name the orchestrator prompt introduces itself with. One constant keeps
# a rename to a one-line change instead of a template edit.
AGENT_IDENTITY: str = os.getenv("AGENT_IDENTITY", "DevForge")
MCP_OAUTH_CALLBACK_URL: str = os.getenv(
    "MCP_OAUTH_CALLBACK_URL", "http://localhost:8000/mcp/oauth/callback"
)

# ── Vision model (multimodal review) ──────────────────────────────────
# Exposed in Settings for image/screenshot review. Defaults to the main agent
# model + endpoint — override only if the multimodal model is served under a
# different id/route than the text agent model.
VISION_MODEL: str = os.getenv("VISION_MODEL", MODEL_NAME)
VISION_BASE_URL: str = os.getenv("VISION_BASE_URL", OPENAI_BASE_URL)
VISION_API_KEY: str = os.getenv("VISION_API_KEY", OPENAI_API_KEY)
# Low temperature — a reviewer should be consistent, not creative.
VISION_TEMPERATURE: float = float(os.getenv("VISION_TEMPERATURE", "0.2"))


# ── Docker ─────────────────────────────────────────────────────────────
DOCKER_IMAGE: str = os.getenv("DOCKER_IMAGE", "python:3.12-slim")
DOCKER_WORKDIR: str = "/workspace"
DOCKER_KEEP_ALIVE: bool = os.getenv("DOCKER_KEEP_ALIVE", "false").lower() in (
    "true",
    "1",
    "yes",
)
# Network mode for the per-chat sandbox. Default "none": the sandbox never
# needs egress — the model call, the validators and the artifact tooling all
# run in the backend process, and the sandbox is reachable only through
# `docker exec`. Leaving it on the default bridge also put the harness API
# (published on 0.0.0.0:8000) and the whole internet one `curl` away from
# agent-authored shell. Set to "bridge" only if an agent must reach a network.
DOCKER_NETWORK: str | None = os.getenv("DOCKER_NETWORK", "none")
# Connection pool size for the Docker SDK HTTP client. Default 10 is too
# low for concurrent exec calls (artifact polling + agent tool execution).
DOCKER_POOL_SIZE: int = int(os.getenv("DOCKER_POOL_SIZE", "25"))
# Docker SDK read timeout. It also bounds ``containers.run``, which takes
# 5-15s on Docker Desktop for Windows, so it must stay well above the exec
# timeout rather than at the 5s the client used to hardcode.
DOCKER_CLIENT_TIMEOUT: int = int(os.getenv("DOCKER_CLIENT_TIMEOUT", "180"))

# ── Sandbox isolation limits ───────────────────────────────────────────
# uid:gid every agent exec runs as (the container itself starts as root only
# to chown the workdir). Empty string = run as the image's default user.
DOCKER_SANDBOX_USER: str = os.getenv("DOCKER_SANDBOX_USER", "1000:1000")
# Hard ceilings so one chat cannot starve the host (or the other chats).
DOCKER_SANDBOX_MEM_LIMIT: str = os.getenv("DOCKER_SANDBOX_MEM_LIMIT", "2g")
DOCKER_SANDBOX_CPUS: float = float(os.getenv("DOCKER_SANDBOX_CPUS", "2.0"))
DOCKER_SANDBOX_PIDS_LIMIT: int = int(os.getenv("DOCKER_SANDBOX_PIDS_LIMIT", "512"))
# Stopped sandboxes older than this are swept at startup. 0 disables the sweep.
DOCKER_ORPHAN_TTL_HOURS: int = int(os.getenv("DOCKER_ORPHAN_TTL_HOURS", "24"))

# ── Thread pool ───────────────────────────────────────────────────────
# AnyIO default is 40 tokens. Bump for I/O-heavy workloads (Docker exec
# calls are I/O-bound, not CPU-bound).
THREAD_POOL_SIZE: int = int(os.getenv("THREAD_POOL_SIZE", "100"))

# ── Orchestrator invocation budget (R2, cost-eval feasibility) ─────────
# Caps the number of LLM model calls per orchestrator run via
# langchain.agents.middleware.ModelCallLimitMiddleware. The 20-trial
# CostEvals batch observed 59-88 invocations (median 71); the subagent
# dispatch count is constant at 7, so the cost tail is orchestrator loop
# iterations, not subagent visits. Ceiling is just above the observed max.
# 0 / unset disables the cap (live chat path keeps unbounded operation).
SDLC_MAX_LLM_INVOCATIONS: int = int(os.getenv("SDLC_MAX_LLM_INVOCATIONS", "0"))

# ── Model context window ──────────────────────────────────────────────
# The model's real input-token limit, used to pick summarization trigger
# thresholds (deepagents uses fraction-based triggers when a profile is
# present, and a conservative fixed 170K trigger when it is not).
#
# This MUST match whatever endpoint OPENAI_BASE_URL points at. It was
# briefly hardcoded to 1,048,576 — correct for deepseek-v4-flash on Ollama
# (verified via POST /api/show) and wrong for anything else. Pointing the
# same code at a 256K-context model would then set the trigger at ~891K:
# summarization would never fire and the provider would hard-error on
# overflow instead, which is a worse failure than compacting too early.
#
# 0 / unset = declare no profile, so deepagents falls back to its fixed
# 170K trigger. That is safe for any model with a window above ~200K and
# merely conservative for larger ones. Set it when you know the number:
#   deepseek-v4-flash (Ollama cloud) -> 1048576
SDLC_MAX_INPUT_TOKENS: int = int(os.getenv("SDLC_MAX_INPUT_TOKENS", "0"))


# ── Artifact cache ────────────────────────────────────────────────────
# Short TTL so the inspector still feels "live" (files appear within ~1s
# of being written) but we avoid hammering the Docker daemon with 15 test
# calls every 2 seconds.
ARTIFACT_CACHE_TTL: float = float(os.getenv("ARTIFACT_CACHE_TTL", "1.0"))

# ── Server ─────────────────────────────────────────────────────────────
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))

# ── Persistence ────────────────────────────────────────────────────────
# Path to the SQLite file backing the LangGraph checkpointer.  Persists
# per-thread conversation memory across server restarts so a chat reopened
# after restart resumes with full message history.  Default sits next to
# the upload dir under backend/.
CHECKPOINT_DB_PATH: str = os.getenv(
    "CHECKPOINT_DB_PATH",
    str(_BACKEND_ROOT / "data" / "checkpoints.sqlite"),
)

# Postgres connection URL for conversations + messages (the production
# replacement for frontend localStorage). Defaults to the local docker
# compose service in docker-compose.yml (`harness:harness@localhost:5432/harness`).
# Override via the DATABASE_URL env var. The driver must be `asyncpg` for
# SQLAlchemy's async engine — we normalise plain `postgresql://` URLs to
# `postgresql+asyncpg://` in sdlc/db/engine.py so deployment configs that
# follow the standard format still work.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/harness",
)

# ── Uploads ────────────────────────────────────────────────────────────
UPLOAD_DIR_HOST: str = os.getenv("UPLOAD_DIR_HOST", str(_BACKEND_ROOT / "uploads"))
MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))

# ── Agent ──────────────────────────────────────────────────────────────
MAX_CONVERSATION_TURNS: int = int(os.getenv("MAX_CONVERSATION_TURNS", "100"))

# ── Auth: sessions + login ─────────────────────────────────────────────
# Opaque server-side sessions in Postgres, delivered as an HttpOnly cookie.
# Not JWT: revocation is a DELETE, and there is no signing key to rotate.
SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "sdlc_session")
SESSION_TTL_DAYS: int = int(os.getenv("SESSION_TTL_DAYS", "14"))
# Set to 1 behind HTTPS. A Secure cookie is simply never sent over plain
# http, so leaving it 0 on localhost is the only working local default.
SESSION_COOKIE_SECURE: bool = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
# "lax" is same-site for localhost:3000 -> localhost:8000 (ports do not
# change the site), so the cookie flows without CSRF tokens. A genuinely
# cross-site deployment needs "none" + SESSION_COOKIE_SECURE=1.
SESSION_COOKIE_SAMESITE: str = os.getenv("SESSION_COOKIE_SAMESITE", "lax")
# Length only, no composition classes — NIST SP 800-63B dropped them, and
# they reject good passphrases while accepting "Passw0rd!".
MIN_PASSWORD_LENGTH: int = int(os.getenv("MIN_PASSWORD_LENGTH", "10"))
# Per-process login throttle: N failures per window per (email, ip) key.
LOGIN_MAX_ATTEMPTS: int = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_WINDOW_MINUTES: int = int(os.getenv("LOGIN_WINDOW_MINUTES", "15"))
# Explicit origins, never "*": browsers refuse to attach credentials to a
# wildcard origin, which silently breaks cookie auth rather than failing open.
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

# ── LangSmith tracing ───────────────────────────────────────────────────
# LangSmith's "Configure" pane suggests LANGSMITH_TRACING, but LangChain
# and LangGraph check LANGCHAIN_TRACING_V2.  We read both; either one
# being truthy activates tracing.
_raw_lcv2 = os.getenv("LANGCHAIN_TRACING_V2", "").lower()
_raw_lstr = os.getenv("LANGSMITH_TRACING", "").lower()
_tracing_requested = _raw_lcv2 in ("true", "1", "yes") or _raw_lstr in (
    "true",
    "1",
    "yes",
)
# A tracer with no key can only 401. `.env` ships LANGCHAIN_TRACING_V2=true
# with an empty LANGSMITH_API_KEY, which made every traced run retry the
# unauthenticated batch upload and delayed process exit by ~10s — visible as
# a slow, noisy test suite rather than as an error. Tracing turns on when it
# can actually authenticate.
LANGCHAIN_TRACING_V2: bool = _tracing_requested and bool(
    os.getenv("LANGSMITH_API_KEY", "").strip()
)

LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "sdlc-harness")
LANGSMITH_ENDPOINT: str = os.getenv(
    "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
)

# Apply LangSmith configuration to os.environ so that LangGraph/LangChain
# auto-tracing picks it up.  We do this after .env loading so that the
# values from .env (override=True) are propagated.
if LANGCHAIN_TRACING_V2:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    if LANGSMITH_API_KEY:
        os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
    if LANGSMITH_PROJECT:
        os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
    if LANGSMITH_ENDPOINT:
        os.environ["LANGSMITH_ENDPOINT"] = LANGSMITH_ENDPOINT
else:
    # Explicitly disable so nothing leaks if system env has them set
    os.environ.pop("LANGCHAIN_TRACING_V2", None)
    os.environ.pop("LANGSMITH_TRACING", None)
    os.environ.pop("LANGSMITH_API_KEY", None)
    os.environ.pop("LANGSMITH_PROJECT", None)
    os.environ.pop("LANGSMITH_ENDPOINT", None)
