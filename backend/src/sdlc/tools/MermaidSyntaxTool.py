"""Mermaid syntax reference lookup, keyed by diagram type or construct.

The per-diagram SKILL.md files carry the worked examples; this tool covers the
gap where the model needs the exact rules for one construct without re-reading
a whole skill.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent / "db" / "mermaid_syntax.yaml"


class MermaidSyntaxTool(BaseTool):
    """Return the Mermaid syntax rules for one diagram type or construct."""

    name: str = "mermaid_syntax_reference_tool"
    description: str = (
        "Get Mermaid syntax rules for a diagram type or construct.\n"
        "Input: a diagram type or construct (e.g. \"erDiagram\", \"class\", "
        "\"state transition\", \"subgraph\", \"cardinality\").\n"
        "Output: the syntax rules and a minimal example.\n"
        "Use only when the diagram skill does not already cover the construct."
    )

    def _load(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Read the YAML reference. Raises if the file is missing or broken."""
        try:
            with _DB_PATH.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except FileNotFoundError:
            msg = f"mermaid_syntax.yaml not found at {_DB_PATH}"
            raise FileNotFoundError(msg) from None
        except yaml.YAMLError as exc:
            msg = f"Error parsing mermaid_syntax.yaml: {exc}"
            raise ValueError(msg) from exc
        return data.get("syntax", {}), data.get("construct_map", {})

    def _run(self, construct_type: str) -> str:
        """Look up *construct_type* in the YAML reference."""
        try:
            syntax, construct_map = self._load()
        except (FileNotFoundError, ValueError) as exc:
            return f"Syntax reference unavailable: {exc}"

        normalised = construct_type.lower().strip()
        key = construct_map.get(normalised, normalised)

        entry = syntax.get(key)
        if entry is None:
            available = sorted(set(syntax) | set(construct_map))
            return (
                f"Syntax reference for {construct_type!r} not found. "
                f"Available: {', '.join(available)}"
            )
        return str(entry)

    async def _arun(self, construct_type: str) -> str:
        """Async wrapper."""
        return self._run(construct_type)

