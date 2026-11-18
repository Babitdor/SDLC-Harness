"""MCP client: turns stored server definitions into LangChain tools.

Why a cache instead of loading on demand: `create_orchestrator()` and
`_build_tools()` are synchronous, while every MCP call is `async`. Loading
inside them would force an event loop into the orchestrator constructor for
every thread. Instead `refresh()` runs from the endpoints (and once at
startup), fills a module cache, and `_build_tools()` reads it synchronously.

Failure policy follows the rest of the harness: an MCP server that will not
connect degrades to "no tools", never to a failed run. The reason is kept per
server so the Settings panel can show it.

`langchain_mcp_adapters` is deprecated upstream in favour of `langchain.mcp`,
which the pinned langchain (1.3.18) does not ship — verified by import. The
import is therefore guarded: without the package the feature is inert, and the
panel reports why instead of erroring.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from sdlc.services import mcp_settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised by the absence branch in tests
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from mcp.client.streamable_http import create_mcp_http_client

    _ADAPTER_ERROR: str | None = None
except ImportError as exc:  # pragma: no cover
    MultiServerMCPClient = None  # type: ignore[assignment]
    _ADAPTER_ERROR = str(exc)

# A remote server that never answers must not stall a settings save.
CONNECT_TIMEOUT = 20.0

# Replaced wholesale on refresh — a reader in another thread sees either the
# old dict or the new one, never a half-filled one.
_CACHE: dict[str, list[Any]] = {}
_STATUS: dict[str, dict[str, Any]] = {}
_refresh_lock = asyncio.Lock()


def available() -> bool:
    """True when the MCP adapter package is importable."""
    return MultiServerMCPClient is not None


def adapter_error() -> str | None:
    return _ADAPTER_ERROR


def _describe_error(exc: BaseException) -> str:
    """Flatten an ExceptionGroup down to the failure a user can act on.

    MCP transports run inside anyio task groups, so a 401 arrives wrapped in an
    ExceptionGroup whose own message is "unhandled errors in a TaskGroup (1
    sub-exception)" — technically true, practically useless. The leaf carries
    the status code, so walk the group (and any __cause__ chain) and report it.

    Every client-side connect failure funnels through here, for both the
    Test button and the startup refresh.
    """
    leaf = exc
    seen = {id(exc)}
    while True:
        nested = getattr(leaf, "exceptions", None)
        nxt: BaseException | None = (
            nested[0] if isinstance(nested, (list, tuple)) and nested else None
        ) or leaf.__cause__ or leaf.__context__
        # A cycle is possible (cause <-> context); stop at the deepest new node.
        if nxt is None or id(nxt) in seen:
            break
        seen.add(id(nxt))
        leaf = nxt

    message = str(leaf).strip() or type(leaf).__name__
    described = f"{type(leaf).__name__}: {message}"
    if leaf is not exc:
        # Keep the outer type visible: "ExceptionGroup" explains WHERE it failed.
        described = f"{described} (from {type(exc).__name__})"
    if "401" in message or "403" in message or "unauthorized" in message.lower():
        described += " - add a credential (Authorization header), then enable it"
    return described


def _connection(server: dict[str, Any]) -> dict[str, Any]:
    if server["transport"] == "stdio":
        conn: dict[str, Any] = {
            "transport": "stdio",
            "command": server["command"],
            "args": list(server.get("args") or []),
        }
        if server.get("env"):
            conn["env"] = dict(server["env"])
        return conn
    conn = {"transport": "http", "url": server["url"]}
    if server.get("headers"):
        conn["headers"] = dict(server["headers"])
    if server.get("oauth"):
        from sdlc.services.mcp_oauth import provider

        conn["headers"] = {k: v for k, v in conn.get("headers", {}).items() if k.lower() != "authorization"}
        conn["auth"] = provider(server)
    return conn


def _http_client(
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    client = create_mcp_http_client(headers=headers, timeout=timeout, auth=auth)

    async def identify(request: httpx.Request) -> None:
        # SDK-created OAuth requests bypass HTTPX defaults; MermaidChart rejects missing User-Agent.
        request.headers.setdefault("User-Agent", client.headers["User-Agent"])

    client.event_hooks["request"].append(identify)
    return client


async def _load_tools(server: dict[str, Any], *, auth: Any = None, timeout: float = CONNECT_TIMEOUT) -> list[Any]:
    """Connect to one server and return its tools. Raises on any failure."""
    if MultiServerMCPClient is None:
        raise RuntimeError(f"langchain-mcp-adapters unavailable: {_ADAPTER_ERROR}")
    connection = _connection(server)
    if auth is not None:
        connection["auth"] = auth
    if connection.get("auth") is not None:
        connection["httpx_client_factory"] = _http_client
    client = MultiServerMCPClient({server["id"]: connection})
    return await asyncio.wait_for(client.get_tools(), timeout=timeout)


async def test_server(server: dict[str, Any]) -> dict[str, Any]:
    """One-shot connection test used by the Settings panel."""
    started = time.monotonic()
    try:
        tools = await _load_tools(server)
    except Exception as exc:  # noqa: BLE001 - surface any transport/auth error verbatim
        logger.warning("MCP test failed for %s: %s", server.get("name"), exc)
        return {
            "ok": False,
            "tools": [],
            "error": _describe_error(exc),
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
    return {
        "ok": True,
        "tools": [t.name for t in tools],
        "error": None,
        "latency_ms": int((time.monotonic() - started) * 1000),
    }


async def refresh() -> dict[str, dict[str, Any]]:
    """Reload every enabled server and rebuild the per-agent tool cache."""
    async with _refresh_lock:
        return await _refresh()


async def _refresh() -> dict[str, dict[str, Any]]:
    global _CACHE, _STATUS

    servers = [s for s in mcp_settings.load_servers() if s["enabled"]]
    cache: dict[str, list[Any]] = {}
    status: dict[str, dict[str, Any]] = {}

    for server in servers:
        started = time.monotonic()
        try:
            tools = await _load_tools(server)
        except Exception as exc:  # noqa: BLE001 - one bad server must not stop the rest
            logger.warning("MCP server %r unavailable: %s", server["name"], exc)
            status[server["id"]] = {
                "server_id": server["id"],
                "name": server["name"],
                "ok": False,
                "tools": [],
                "error": _describe_error(exc),
                "checked_at": time.time(),
                "latency_ms": int((time.monotonic() - started) * 1000),
            }
            continue

        for agent in server["agents"]:
            cache.setdefault(agent, []).extend(tools)
        status[server["id"]] = {
            "server_id": server["id"],
            "name": server["name"],
            "ok": True,
            "tools": [t.name for t in tools],
            "error": None,
            "checked_at": time.time(),
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
        logger.info(
            "MCP server %r loaded %d tool(s) for %s",
            server["name"],
            len(tools),
            ", ".join(server["agents"]) or "no agents",
        )

    _CACHE = cache
    _STATUS = status
    return status


def tools_for(agent: str) -> list[Any]:
    """Cached MCP tools assigned to *agent* (empty when none are loaded)."""
    return list(_CACHE.get(agent, ()))


def tools_for_all() -> dict[str, list[Any]]:
    return {agent: list(tools) for agent, tools in _CACHE.items() if tools}


def status() -> dict[str, dict[str, Any]]:
    return dict(_STATUS)


def clear() -> None:
    """Drop the cache (tests; also after a server is deleted)."""
    global _CACHE, _STATUS
    _CACHE, _STATUS = {}, {}
