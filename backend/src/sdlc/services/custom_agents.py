"""Storage layer for user-created subagents.

Custom agents are stored as a JSON list under ``backend/data/custom_agents.json``.
Each entry has an ``id`` (uuid4), a display ``name``, a ``description``, a
``system_prompt``, and a list of ``tools`` (registry keys resolved to BaseTool
instances at orchestrator-build time). They are merged into the orchestrator's
subagent roster at ``create_orchestrator()`` time — see ``agent.py``.

Mutations (create/update/delete) drop every cached orchestrator via
``_invalidate_all_orchestrators()`` in ``app.py``, so changes propagate to
*every* chat — old and new — on its next message, not just freshly-created ones.

The file is read on every call (no in-memory cache) to keep the model simple:
the volume is tiny (dozens of records max) and edits should be visible
immediately to the next session.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from langchain.agents.middleware import ModelRetryMiddleware

from sdlc.core.config import CHECKPOINT_DB_PATH

logger = logging.getLogger(__name__)

# Stored next to the checkpoint sqlite so all backend persistence lives in
# the same data directory.
_CUSTOM_AGENTS_PATH = Path(CHECKPOINT_DB_PATH).parent / "custom_agents.json"

# Single-process write lock. Concurrent FastAPI requests writing to the
# same file would otherwise race and clobber each other.
_write_lock = threading.Lock()

# Subagent names that shadow built-ins are rejected at create/update time
# so a custom agent can't silently override the orchestrator's wiring.
_RESERVED_NAMES = {
    "ingestion",
    "requirements",
    "architecture",
    "api",
    "planning",
    "devops",
    "diagram",
    "general-purpose",
}

# Deep-agents names must be lowercase alphanumeric + hyphens. We canonicalise
# user-supplied names to this shape before storing them.
_NAME_NORMALISE = re.compile(r"[^a-z0-9-]+")

# ── Tool registry ──────────────────────────────────────────────────────────
#
# Canonical mapping of tool category keys → human-readable metadata.
# Used by the frontend to show a tool-selection checklist and by
# resolve_tools() to map user selections to actual tool instances.
#
# The "tools" list contains the BaseTool.name values that identify each
# tool in the category. These names must match what _build_tools() in
# subagents.py produces.

TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "diagram": {
        "label": "Mermaid Diagrams",
        "description": "Mermaid syntax validation and per-diagram-type syntax reference",
        "tools": ["mermaid-validator-tool", "mermaid_syntax_reference_tool"],
    },
    "api": {
        "label": "OpenAPI Validation",
        "description": "Validate an OpenAPI 3.0 document against the spec schema",
        "tools": ["openapi_validator_tool"],
    },
    "planning": {
        "label": "Gherkin Validation",
        "description": "Parse and validate Given/When/Then Gherkin feature files",
        "tools": ["gherkin_validator_tool"],
    },
    "devops": {
        "label": "CI Pipeline Validation",
        "description": "Validate a GitHub Actions workflow file (YAML parse + required keys)",
        "tools": ["ci_pipeline_validator_tool"],
    },
    "web_search": {
        "label": "Web Search",
        "description": "Search the web via DuckDuckGo for external information",
        "tools": ["web_search"],
    },
}


def get_tool_registry() -> dict[str, dict[str, Any]]:
    """Return the tool registry with availability status.

    Each entry gets an ``available`` boolean indicating whether the
    underlying tool(s) can be instantiated at runtime.  This lets the
    frontend grey out options whose dependencies are missing (e.g. an
    uninstalled validator package).
    """
    registry = {}
    for key, meta in TOOL_REGISTRY.items():
        registry[key] = {**meta, "available": _check_tool_available(key)}
    return registry


def _check_tool_available(category: str) -> bool:
    """Return True if at least one tool in *category* can be instantiated."""
    try:
        from sdlc.services.subagents import _build_tools
        tools_map = _build_tools()
        # Orchestrator-level tools are built separately — check those too
        from sdlc.services.subagents import _build_orchestrator_tools
        orch_tools = _build_orchestrator_tools()
    except Exception:
        return False

    category_tools = tools_map.get(category, [])
    if category_tools:
        return True

    # Check if any orchestrator tool name matches this category
    meta = TOOL_REGISTRY.get(category, {})
    expected_names = set(meta.get("tools", []))
    if expected_names and any(t.name in expected_names for t in orch_tools):
        return True

    return False


def resolve_tools(tool_keys: list[str]) -> list[Any]:
    """Resolve tool category keys to actual BaseTool instances.

    Iterates *tool_keys*, looks each up in ``TOOL_REGISTRY``, fetches
    the corresponding tool instances from ``_build_tools()`` and
    ``_build_orchestrator_tools()``, and returns the matching tools.

    Unknown keys and tools whose dependencies are missing are silently
    skipped with a debug log.
    """
    if not tool_keys:
        return []

    from sdlc.services.subagents import _build_tools, _build_orchestrator_tools

    tools_map = _build_tools()
    orch_tools = _build_orchestrator_tools()

    # Build a name→instance lookup from both sources
    name_to_tool: dict[str, Any] = {}
    for tool_list in tools_map.values():
        for t in tool_list:
            name_to_tool[t.name] = t
    for t in orch_tools:
        name_to_tool[t.name] = t

    resolved: list[Any] = []
    for key in tool_keys:
        meta = TOOL_REGISTRY.get(key)
        if meta is None:
            logger.debug("Unknown tool category %r — skipping", key)
            continue
        for tool_name in meta["tools"]:
            tool = name_to_tool.get(tool_name)
            if tool is not None:
                resolved.append(tool)
            else:
                logger.debug(
                    "Tool %r (category %r) not available — skipping",
                    tool_name, key,
                )

    return resolved


def _normalise_name(name: str) -> str:
    """Canonicalise a display name to a deep-agents-safe identifier."""
    lowered = name.strip().lower().replace(" ", "-")
    cleaned = _NAME_NORMALISE.sub("", lowered).strip("-")
    return cleaned[:64] or "agent"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_tool_keys(tools: list[str]) -> None:
    """Validate that all tool keys are known. Raises ValueError for unknown keys."""
    unknown = [k for k in tools if k not in TOOL_REGISTRY]
    if unknown:
        known = sorted(TOOL_REGISTRY.keys())
        msg = (
            f"Unknown tool key(s): {unknown}. "
            f"Valid keys: {known}"
        )
        raise ValueError(msg)


def _load_raw() -> list[dict[str, Any]]:
    """Load the raw list from disk. Returns [] if the file doesn't exist or is malformed."""
    if not _CUSTOM_AGENTS_PATH.exists():
        return []
    try:
        with _CUSTOM_AGENTS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.warning("custom_agents.json is not a list — treating as empty")
            return []
        return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read custom_agents.json: %s — treating as empty", exc)
        return []


def _save_raw(agents: list[dict[str, Any]]) -> None:
    """Atomically write the list to disk."""
    _CUSTOM_AGENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _CUSTOM_AGENTS_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(agents, f, indent=2, ensure_ascii=False)
    tmp.replace(_CUSTOM_AGENTS_PATH)


# ── Public CRUD API ─────────────────────────────────────────────────────


def list_custom_agents() -> list[dict[str, Any]]:
    """Return all custom agents."""
    return _load_raw()


def get_custom_agent(agent_id: str) -> dict[str, Any] | None:
    for a in _load_raw():
        if a.get("id") == agent_id:
            return a
    return None


def create_custom_agent(
    name: str,
    description: str,
    system_prompt: str,
    tools: list[str] | None = None,
) -> dict[str, Any]:
    """Add a new custom agent. Raises ValueError on validation failure."""
    canonical = _normalise_name(name)
    if canonical in _RESERVED_NAMES:
        msg = f"Agent name '{canonical}' is reserved (shadows a built-in subagent)"
        raise ValueError(msg)

    # Validate tool keys against the registry
    if tools is not None:
        _validate_tool_keys(tools)

    with _write_lock:
        agents = _load_raw()
        if any(_normalise_name(a.get("name", "")) == canonical for a in agents):
            msg = f"An agent named '{canonical}' already exists"
            raise ValueError(msg)
        entry = {
            "id": str(uuid.uuid4()),
            "name": name.strip(),
            "description": description.strip(),
            "system_prompt": system_prompt,
            "tools": tools or [],
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        agents.append(entry)
        _save_raw(agents)
        logger.info("Created custom agent %s (%s)", entry["id"], canonical)
        return entry


def update_custom_agent(
    agent_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    system_prompt: str | None = None,
    tools: list[str] | None = None,
) -> dict[str, Any] | None:
    """Update an existing agent's editable fields. Returns the updated entry, or None if not found."""
    if tools is not None:
        _validate_tool_keys(tools)

    with _write_lock:
        agents = _load_raw()
        idx = next((i for i, a in enumerate(agents) if a.get("id") == agent_id), None)
        if idx is None:
            return None

        entry = dict(agents[idx])
        if name is not None:
            canonical = _normalise_name(name)
            if canonical in _RESERVED_NAMES:
                msg = f"Agent name '{canonical}' is reserved"
                raise ValueError(msg)
            # Reject if another agent already uses this canonical name
            for j, a in enumerate(agents):
                if j == idx:
                    continue
                if _normalise_name(a.get("name", "")) == canonical:
                    msg = f"Another agent named '{canonical}' already exists"
                    raise ValueError(msg)
            entry["name"] = name.strip()
        if description is not None:
            entry["description"] = description.strip()
        if system_prompt is not None:
            entry["system_prompt"] = system_prompt
        if tools is not None:
            entry["tools"] = tools
        entry["updated_at"] = _now_iso()
        agents[idx] = entry
        _save_raw(agents)
        logger.info("Updated custom agent %s", agent_id)
        return entry


def delete_custom_agent(agent_id: str) -> bool:
    """Remove an agent. Returns True if it existed."""
    with _write_lock:
        agents = _load_raw()
        before = len(agents)
        agents = [a for a in agents if a.get("id") != agent_id]
        if len(agents) == before:
            return False
        _save_raw(agents)
        logger.info("Deleted custom agent %s", agent_id)
        return True


# ── Orchestrator integration ────────────────────────────────────────────


def custom_agents_as_subagent_specs() -> list[dict[str, Any]]:
    """Return the custom agents shaped as deep-agents subagent specs.

    Used by ``create_orchestrator`` to merge user-created agents into the
    static ``ALL_SUBAGENTS`` roster. Each spec includes the agent's
    selected domain tools (resolved from the ``tools`` field) in addition
    to the default deep-agent toolset (read_file, write_file, ls, execute,
    etc.).
    """
    specs: list[dict[str, Any]] = []
    for entry in _load_raw():
        canonical = _normalise_name(entry.get("name", ""))
        if not canonical or canonical in _RESERVED_NAMES:
            # Defensive — should have been caught at create/update time, but
            # we'd rather silently drop a malformed entry than crash the
            # orchestrator factory.
            logger.warning("Skipping malformed custom agent: %r", entry)
            continue

        tool_keys: list[str] = entry.get("tools", [])
        agent_tools = resolve_tools(tool_keys)
        if agent_tools:
            logger.info(
                "Attached %d tool(s) to custom agent '%s': %s",
                len(agent_tools),
                canonical,
                [t.name for t in agent_tools],
            )

        specs.append(
            {
                "name": canonical,
                "description": entry.get("description", "").strip(),
                "system_prompt": entry.get("system_prompt", ""),
                "tools": agent_tools,
                "middleware": [
                    ModelRetryMiddleware(
                        max_retries=3,
                        backoff_factor=2.0,
                        initial_delay=1.0,
                    ),
                ],
            }
        )
    return specs
