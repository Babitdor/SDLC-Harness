"""Storage for user-configured MCP servers.

Mirrors :mod:`sdlc.services.model_settings`: one JSON file beside the
checkpoint database, an atomic replace, and a lock so two concurrent
settings writes cannot tear the file.

There is no env/default fallback layer — MCP servers only ever come from the
Settings UI, so the store *is* the source of truth. That differs from model
settings on purpose: a half-configured remote server is worse than none.

Credentials live in the per-server `env` / `headers` maps (PATs, bearer
tokens, API keys). Their values are never returned to the client; the public
shape exposes key names only. Credential updates merge by key, with HTTP
header names compared case-insensitively so rotation replaces the old value.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sdlc.core import config

logger = logging.getLogger(__name__)

_STORE_PATH = Path(config.CHECKPOINT_DB_PATH).parent / "mcp_settings.json"
_lock = threading.Lock()

TRANSPORTS = ("stdio", "http")
# Mirrors the roster in services/subagents.py. Duplicated as a literal because
# importing that module renders every Jinja prompt at import time.
AGENT_KEYS = ("ingestion", "requirements", "architecture", "api", "planning", "devops", "diagram")
SECRET_MAPS = ("env", "headers")
_PUBLIC_KEYS = (
    "id",
    "name",
    "description",
    "credential_hint",
    "transport",
    "enabled",
    "command",
    "args",
    "url",
    "agents",
)


def _pick(data: dict[str, Any], existing: dict[str, Any], key: str, default: Any) -> Any:
    """Return *data[key]* if the caller sent it, else the stored value."""
    if key in data:
        return data[key]
    return existing.get(key, default)


def _coerce_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(k): str(v) for k, v in value.items() if str(k).strip()}


def _normalise(
    data: dict[str, Any], existing: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Validate and coerce one server record. Raises ValueError on bad input."""
    base = existing or {}
    transport = str(_pick(data, base, "transport", "stdio")).lower().strip()
    if transport not in TRANSPORTS:
        raise ValueError(f"unknown transport {transport!r} (expected one of {', '.join(TRANSPORTS)})")

    name = str(_pick(data, base, "name", "")).strip()
    if not name:
        raise ValueError("server name is required")

    command = str(_pick(data, base, "command", "") or "").strip()
    url = str(_pick(data, base, "url", "") or "").strip()
    if transport == "stdio" and not command:
        raise ValueError("stdio servers need a command")
    if transport == "http" and not url:
        raise ValueError("http servers need a url")
    if transport == "http":
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("http servers need an http(s) URL without credentials or a fragment")

    raw_args = _pick(data, base, "args", [])
    args = [str(a) for a in raw_args] if isinstance(raw_args, list) else []

    raw_agents = _pick(data, base, "agents", [])
    agents = [a for a in (str(x) for x in raw_agents) if a in AGENT_KEYS] if isinstance(raw_agents, list) else []

    env = _coerce_map(_pick(data, base, "env", {}))
    headers = _coerce_map(_pick(data, base, "headers", {}))

    description = str(_pick(data, base, "description", "") or "").strip()
    # Free text telling the user WHICH credential to paste, e.g.
    # "Authorization: Bearer <PAT>". Presets carry it; a user-created server
    # can too. It is never a secret, so it round-trips like the description.
    credential_hint = str(_pick(data, base, "credential_hint", "") or "").strip()

    return {
        "id": str(base.get("id") or uuid.uuid4().hex[:8]),
        "name": name,
        "description": description,
        "credential_hint": credential_hint,
        "transport": transport,
        "enabled": bool(_pick(data, base, "enabled", True)),
        "command": command,
        "args": args,
        "url": url,
        "env": env,
        "headers": headers,
        "agents": agents,
        "oauth": dict(base.get("oauth") or {}),
    }


def _read_store() -> tuple[list[dict[str, Any]], bool]:
    """Return (servers, presets_seeded). Tolerates both file shapes.

    The flag exists so boot-time seeding happens exactly once: re-adding the
    catalog on every restart would resurrect servers the user deliberately
    deleted. Restoring it explicitly is an endpoint, not a side effect.
    """
    if not _STORE_PATH.exists():
        return [], False
    try:
        with _STORE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read mcp_settings.json: %s — treating as empty", exc)
        return [], False

    if isinstance(data, dict):
        servers = data.get("servers")
        seeded = bool(data.get("presets_seeded"))
    else:  # bare list written by an older build
        servers, seeded = data, False
    if not isinstance(servers, list):
        logger.warning("mcp_settings.json has no servers list — treating as empty")
        return [], seeded

    out: list[dict[str, Any]] = []
    for entry in servers:
        if not isinstance(entry, dict):
            continue
        try:
            out.append(_normalise(entry, existing=entry))
        except ValueError as exc:
            logger.warning("Skipping invalid stored MCP server %r: %s", entry.get("name"), exc)
    return out, seeded


def _load_raw() -> list[dict[str, Any]]:
    return _read_store()[0]


def _save_raw(
    servers: list[dict[str, Any]], *, presets_seeded: bool | None = None
) -> None:
    if presets_seeded is None:
        _, presets_seeded = _read_store()  # preserve the existing flag
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _STORE_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(
            {"servers": servers, "presets_seeded": presets_seeded},
            f,
            indent=2,
            ensure_ascii=False,
        )
    tmp.replace(_STORE_PATH)


def _public(server: dict[str, Any]) -> dict[str, Any]:
    """Client-safe view: credential values replaced by their key names."""
    out = {k: server[k] for k in _PUBLIC_KEYS}
    out["args"] = list(server["args"])
    out["agents"] = list(server["agents"])
    out["env_keys"] = sorted(server["env"])
    out["header_keys"] = sorted(server["headers"])
    out["oauth_connected"] = bool(server.get("oauth", {}).get("tokens"))
    return out


# ── Public API ──────────────────────────────────────────────────────────


def load_servers() -> list[dict[str, Any]]:
    """Every stored server, WITH credential values — internal use only."""
    return _load_raw()


def public_servers() -> list[dict[str, Any]]:
    return [_public(s) for s in _load_raw()]


def get_server(server_id: str) -> dict[str, Any] | None:
    return next((s for s in _load_raw() if s["id"] == server_id), None)


def public_server(server_id: str) -> dict[str, Any] | None:
    server = get_server(server_id)
    return _public(server) if server else None


def create_server(data: dict[str, Any]) -> dict[str, Any]:
    server = _normalise(data)
    with _lock:
        servers = _load_raw()
        servers.append(server)
        _save_raw(servers)
    logger.info("MCP server added: %s (%s)", server["name"], server["transport"])
    return server


def update_server(server_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Patch one server; credentials merge at key level.

    Sending {"Authorization": "<new token>"} upserts that one header and leaves
    every other stored header untouched. Replacing the map wholesale - the
    original behaviour - meant editing a description silently dropped the token
    the user had pasted. Passthrough clear_credentials=True to wipe them.
    """
    payload = dict(data)
    clear = bool(payload.pop("clear_credentials", False))

    with _lock:
        servers, seeded = _read_store()
        for index, existing in enumerate(servers):
            if existing["id"] != server_id:
                continue
            patch = dict(payload)
            for kind in SECRET_MAPS:
                if clear:
                    patch[kind] = {}
                elif kind in patch:
                    incoming = _coerce_map(patch[kind])
                    kept = existing[kind]
                    if kind == "headers":
                        names = {key.lower() for key in incoming}
                        kept = {k: v for k, v in kept.items() if k.lower() not in names}
                    patch[kind] = {**kept, **incoming}
            merged = _normalise(patch, existing=existing)
            if clear or merged["url"] != existing["url"] or merged["transport"] != existing["transport"]:
                merged["oauth"] = {}
            elif any(k.lower() == "authorization" for k in payload.get("headers", {}) or {}):
                merged["oauth"] = {}
            servers[index] = merged
            _save_raw(servers, presets_seeded=seeded)
            return merged
    raise KeyError(server_id)


def save_oauth(server_id: str, oauth: dict[str, Any], *, generation: str | None = None) -> None:
    """Internal credential write; reject callbacks for cleared/replaced connections."""
    with _lock:
        servers, seeded = _read_store()
        for server in servers:
            if server["id"] != server_id:
                continue
            if generation is not None and server["oauth"].get("generation") != generation:
                raise ValueError("OAuth connection changed; connect again")
            server["oauth"] = oauth
            _save_raw(servers, presets_seeded=seeded)
            return
    raise ValueError("MCP server no longer exists")


def delete_server(server_id: str) -> bool:
    with _lock:
        servers = _load_raw()
        remaining = [s for s in servers if s["id"] != server_id]
        if len(remaining) == len(servers):
            return False
        _save_raw(remaining)
    logger.info("MCP server removed: %s", server_id)
    return True

# ── Preset catalog ──────────────────────────────────────────────────────
#
# The phase-mapped shortlist: each entry names the agents that gain tools and
# the artifact it improves. Remote URLs are the vendors' own published
# endpoints, verified against the MCP registry / vendor docs on 2026-11-16.
#
# Servers that need a credential ship DISABLED. Seeding an unauthenticated
# server only paints a failed row and still leaves the user pasting a token,
# so the catalog states the prerequisite instead of pretending it works.
PRESETS: list[dict[str, Any]] = [
    {
        "name": "fetch",
        "description": "URL/PDF -> clean text for sources/. No auth.",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "agents": ["ingestion"],
        "enabled": True,
    },
    {
        "name": "context7",
        "description": "Library docs so ADRs and API specs stop inventing APIs/versions. Anonymous works.",
        "transport": "http",
        "url": "https://mcp.context7.com/mcp",
        "agents": ["architecture", "api"],
        "enabled": True,
    },
    {
        "name": "atlassian",
        "description": "Confluence page trees as sources + Jira epics for USER_STORIES. Needs an OAuth bearer token.",
        "transport": "http",
        "url": "https://mcp.atlassian.com/v2/mcp",
        "agents": ["ingestion", "requirements", "planning"],
        "enabled": False,
    },
    {
        "name": "notion",
        "description": "Notion workspaces as source material. Needs a Notion integration token.",
        "transport": "http",
        "url": "https://mcp.notion.com/mcp",
        "agents": ["ingestion"],
        "enabled": False,
    },
    {
        "name": "linear",
        "description": "Real issues/projects/cycles behind REQUIREMENTS and BACKLOG. Needs a Linear API key.",
        "transport": "http",
        "url": "https://mcp.linear.app/mcp",
        "agents": ["requirements", "planning"],
        "enabled": False,
    },
    {
        "name": "github",
        "description": "Read the existing repo + workflows, and push BACKLOG to issues. Needs a PAT with repo scope.",
        "transport": "http",
        "url": "https://api.githubcopilot.com/mcp/",
        "agents": ["architecture", "planning", "devops"],
        "enabled": False,
    },
    {
        "name": "terraform",
        "description": "Provider docs/schemas for IaC-accurate topology. Needs the docker CLI in this image; edit command and args for a remote registry.",
        "transport": "stdio",
        "command": "docker",
        "args": ["run", "-i", "--rm", "hashicorp/terraform-mcp-server"],
        "agents": ["architecture", "devops"],
        "enabled": False,
    },
    {
        "name": "postman",
        "description": "Publish the validated openapi.yaml as a reviewable collection. Needs a Postman API key.",
        "transport": "http",
        "url": "https://mcp.postman.com/mcp",
        "agents": ["api"],
        "enabled": False,
    },
    {
        "name": "mermaidchart",
        "description": "Server-side Mermaid render/validate so diagrams become SVG artifacts. Needs a Mermaid Chart token.",
        "transport": "http",
        "url": "https://mcp.mermaidchart.com/mcp",
        "agents": ["diagram"],
        "enabled": False,
    },
]


# What the user has to paste for each preset. Every hosted preset
# authenticates with a bearer header; terraform takes an env var. The panel
# shows this as the credential placeholder, so "add an API key" has a shape.
_PRESET_HINTS: dict[str, str] = {
    "atlassian": "Authorization: Bearer <token>",
    "notion": "Authorization: Bearer <integration token>",
    "linear": "Authorization: Bearer <api key>",
    "github": "Authorization: Bearer <PAT>",
    "postman": "Authorization: Bearer <postman api key>",
    "mermaidchart": "Authorization: Bearer <token>",
    "terraform": "TFE_TOKEN=<token>",
}


def seed_presets(*, force: bool = False) -> list[dict[str, Any]]:
    """Insert missing presets and backfill credential hints.

    Boot calls this once; the API calls it with force=True to restore the
    catalog after the user deletes entries. Existing servers are never
    overwritten - an edited command or pasted token always wins - but an empty
    credential_hint is filled in, so a catalog seeded before hints existed still
    tells the user what to paste.
    """
    with _lock:
        servers, seeded = _read_store()
        added: list[dict[str, Any]] = []
        changed = False

        for index, server in enumerate(servers):
            hint = _PRESET_HINTS.get(server["name"], "")
            if hint and not server["credential_hint"]:
                servers[index] = {**server, "credential_hint": hint}
                changed = True

        if force or not seeded:
            existing = {s["name"] for s in servers}
            for preset in PRESETS:
                if preset["name"] in existing:
                    continue
                record = _normalise(
                    {**preset, "credential_hint": _PRESET_HINTS.get(preset["name"], "")}
                )
                servers.append(record)
                added.append(record)
                changed = True

        if changed:
            _save_raw(servers, presets_seeded=True)

    if added:
        logger.info("MCP presets seeded: %s", ", ".join(s["name"] for s in added))
    return added
