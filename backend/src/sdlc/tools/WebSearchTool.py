"""Web search tool for the orchestrator (DuckDuckGo, no API key).

Wraps `langchain_community.tools.DuckDuckGoSearchResults` so the
orchestrator can look up real-world information when delegation-based
context isn't enough — checking standards, looking up domain references,
verifying a fact the user mentioned, etc.

Sub-agents are deliberately NOT given this tool: their outputs must
stay deterministic and traceable to the structured artifacts that flow
through `/workspace/project_*/`. The orchestrator is the only place
where external information is appropriate.

If `langchain-community` or `duckduckgo-search` is missing at runtime,
`build_web_search_tools()` returns an empty list and logs a warning so
the backend still boots — same pattern as `_build_tools()` uses for the
validator tools.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Hard cap on results returned to the agent. DuckDuckGo regularly returns
# 20-30 snippets; for orchestrator-level usage 5 is enough to inform a
# decision without burying the model in noise.
_DEFAULT_MAX_RESULTS = 5
_HARD_MAX_RESULTS = 10


class WebSearchInput(BaseModel):
    """Input schema for `web_search`."""

    query: str = Field(
        ...,
        description=(
            "The search query — phrase it as you would for a search engine, "
            "not as a question. Be specific: include domain keywords, "
            "version numbers, and any disambiguating context."
        ),
    )
    max_results: int = Field(
        _DEFAULT_MAX_RESULTS,
        description=(
            f"How many results to return (1–{_HARD_MAX_RESULTS}). "
            f"Default {_DEFAULT_MAX_RESULTS}; raise only when the first "
            "result set didn't cover the answer."
        ),
        ge=1,
        le=_HARD_MAX_RESULTS,
    )


class WebSearchTool(BaseTool):
    """Read-only DuckDuckGo web search.

    Returns a newline-separated list of `[title] snippet (url)` rows so the
    model can scan results in one read. Use `task` to delegate the actual
    work; this tool is for grounding the orchestrator's own decisions.
    """

    name: str = "web_search"
    description: str = (
        "Search the public web via DuckDuckGo for information that isn't in "
        "the workspace artifacts. Use to: verify a domain fact the user "
        "mentioned, look up a standard / spec / regulation, find a reference "
        "implementation for a sub-agent to mirror, or check terminology in a "
        "specialist field (logistics, automotive, aerospace) before delegating. "
        "DO NOT use for queries that should be answered by an existing artifact, "
        "or for casual / opinion-style questions. Returns up to "
        f"{_HARD_MAX_RESULTS} results in a `[title] snippet (url)` format."
    )
    args_schema: type[BaseModel] = WebSearchInput

    # Filled in at construction; private attr to keep BaseTool's Pydantic
    # introspection happy.
    _ddg: Any = None

    def __init__(self, ddg_runnable: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Bypass BaseModel's setattr restrictions — `_ddg` is a private
        # attribute not declared in the schema.
        object.__setattr__(self, "_ddg", ddg_runnable)

    def _run(self, query: str, max_results: int = _DEFAULT_MAX_RESULTS) -> str:
        # Clamp defensively — agent could pass values outside the schema if
        # the wire-format check is bypassed.
        n = max(1, min(int(max_results), _HARD_MAX_RESULTS))
        try:
            # DuckDuckGoSearchResults exposes `.invoke({"query": ...})` in
            # modern langchain-community and also a plain `.run(query)`
            # callable. Prefer invoke for forward compatibility.
            raw = self._ddg.invoke({"query": query})
        except Exception as exc:
            logger.warning("web_search failed for query %r: %s", query, exc)
            return (
                f"ERROR: web search failed — {exc}. "
                "Either the query was rate-limited or the search service is "
                "unreachable. Retry once or proceed without external context."
            )

        # `raw` is typically a string of `snippet: ..., title: ..., link: ...`
        # entries; we keep DuckDuckGo's native formatting but truncate to
        # `n` records so the model gets a tight, scannable list.
        if not raw:
            return f"No results for {query!r}."
        # The wrapper returns one record per line as `snippet: ..., title: ...`
        # We split on the conventional separator and take the first n.
        lines = [line.strip() for line in str(raw).split("], [") if line.strip()]
        head = lines[:n] if len(lines) > n else lines
        return "\n".join(head)


def build_web_search_tools() -> list[BaseTool]:
    """Construct the web-search tool list for the orchestrator.

    Returns an empty list (with a warning log) if `langchain-community` or
    `duckduckgo-search` is missing — keeps the backend bootable on stripped
    environments. Same pattern as the optional validator builders.
    """
    try:
        # Defer the import so a missing dep doesn't break module load. The
        # community wrapper is a thin LangChain BaseTool around the
        # duckduckgo-search package's HTTP client.
        from langchain_community.tools import DuckDuckGoSearchResults
    except ImportError as exc:
        logger.warning(
            "DuckDuckGoSearchResults unavailable (langchain-community missing): %s",
            exc,
        )
        return []

    try:
        # Smoke-check the underlying client too — `ddgs` is a separate
        # package (renamed from `duckduckgo-search`) and might be
        # uninstalled even if langchain-community is present. Modern
        # langchain-community insists on this exact import name.
        import ddgs  # noqa: F401  (presence-check only)
    except ImportError as exc:
        logger.warning(
            "ddgs package unavailable — web_search disabled: %s", exc,
        )
        return []

    try:
        ddg = DuckDuckGoSearchResults(
            num_results=_HARD_MAX_RESULTS,
            output_format="list",
        )
    except TypeError:
        # Older langchain-community signatures may not accept
        # `output_format` — fall back to defaults.
        ddg = DuckDuckGoSearchResults(num_results=_HARD_MAX_RESULTS)

    tool = WebSearchTool(ddg_runnable=ddg)
    logger.info("Loaded WebSearchTool (DuckDuckGo) for orchestrator")
    return [tool]
