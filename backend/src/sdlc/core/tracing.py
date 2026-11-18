"""LangSmith tracing — configuration helpers only.

LangSmith tracing for LangGraph / deepagents is automatic once the
standard environment variables are set:

    LANGSMITH_TRACING=true           (or LANGCHAIN_TRACING_V2=true)
    LANGSMITH_API_KEY=<your-key>
    LANGSMITH_ENDPOINT=https://api.smith.langchain.com
    LANGSMITH_PROJECT=<your-project>

``sdlc.core.config`` forwards these into ``os.environ`` at import time,
so the runtime picks them up without any further setup.

This module exposes only what the rest of the app actually needs:

  - :func:`is_tracing_enabled` — cheap guard for opt-in code paths.
  - :func:`setup_tracing`      — verify connectivity once at startup,
    return a status dict for the ``/tracing`` endpoint.
  - :func:`make_trace_metadata` — tag dict forwarded as LangGraph
    ``config["metadata"]`` so traces are searchable by project/thread.
"""

from __future__ import annotations

import logging
from typing import Any

from langsmith import Client

from sdlc.core.config import (
    LANGCHAIN_TRACING_V2,
    LANGSMITH_API_KEY,
    LANGSMITH_ENDPOINT,
    LANGSMITH_PROJECT,
)

logger = logging.getLogger(__name__)


def is_tracing_enabled() -> bool:
    """True when both the tracing flag and an API key are set."""
    return LANGCHAIN_TRACING_V2 and bool(LANGSMITH_API_KEY)


def setup_tracing() -> dict[str, Any]:
    """Verify LangSmith connectivity at startup. Safe when disabled."""
    info: dict[str, Any] = {
        "tracing_enabled": is_tracing_enabled(),
        "project": LANGSMITH_PROJECT,
        "endpoint": LANGSMITH_ENDPOINT,
        "api_key_set": bool(LANGSMITH_API_KEY),
        "status": "disabled",
    }

    if not is_tracing_enabled():
        return info

    try:
        Client(api_key=LANGSMITH_API_KEY, api_url=LANGSMITH_ENDPOINT).list_runs(limit=1)
        info["status"] = "connected"
        logger.info("LangSmith tracing active (project=%s)", LANGSMITH_PROJECT)
    except Exception as exc:  # noqa: BLE001
        info["status"] = "error"
        info["error"] = str(exc)
        logger.warning("LangSmith connectivity check failed: %s", exc)

    return info


def make_trace_metadata(
    project_id: str,
    thread_id: str,
    agent_name: str | None = None,
) -> dict[str, Any]:
    """Build the metadata dict we attach to LangGraph ``config``.

    Tagging every run with ``project_id`` / ``thread_id`` lets you filter
    in LangSmith without inspecting message contents.
    """
    meta: dict[str, Any] = {"project_id": project_id, "thread_id": thread_id}
    if agent_name:
        meta["subagent"] = agent_name
    return meta
