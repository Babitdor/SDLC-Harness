"""Gherkin feature-file validator.

@Planning writes acceptance criteria as Given/When/Then; this tool parses the
same text the way Cucumber would, so a malformed criterion is caught before it
reaches a test runner.
"""

from __future__ import annotations

import logging

from langchain.tools import BaseTool

logger = logging.getLogger(__name__)


class GherkinValidatorTool(BaseTool):
    """Parse a Gherkin document and report parse errors with line numbers."""

    name: str = "gherkin_validator_tool"
    description: str = (
        "Validate Gherkin (Given/When/Then) feature text.\n"
        "Input: the complete feature file text, starting with `Feature:`.\n"
        "Output: PASS plus the scenario count, or FAIL plus each parse error "
        "and its line.\n"
        "Use when a test plan expresses acceptance criteria as Gherkin."
    )

    def _run(self, document: str) -> str:
        """Parse *document* and return a human-readable verdict."""
        try:
            from gherkin.errors import CompositeParserException
            from gherkin.parser import Parser
        except ImportError:
            logger.warning("gherkin-official not installed — structural fallback")
            return self._structural_check(document)

        try:
            doc = Parser().parse(document)
        except CompositeParserException as exc:
            errors = "\n".join(f"  - {e}" for e in exc.errors)
            return f"FAIL — {len(exc.errors)} parse error(s):\n{errors}"
        except Exception as exc:
            return f"FAIL — {type(exc).__name__}: {exc}"

        feature = doc.get("feature") or {}
        children = feature.get("children") or []
        n_scenarios = sum(1 for c in children if "scenario" in c)
        name = feature.get("name") or "<unnamed>"
        return f"PASS — feature {name!r}, {n_scenarios} scenario(s)."

    def _structural_check(self, document: str) -> str:
        """Fallback: require a Feature line and at least one Scenario."""
        lines = [ln.strip() for ln in document.splitlines()]
        has_feature = any(ln.startswith("Feature:") for ln in lines)
        has_scenario = any(
            ln.startswith(("Scenario:", "Scenario Outline:")) for ln in lines
        )
        problems = []
        if not has_feature:
            problems.append("no `Feature:` line")
        if not has_scenario:
            problems.append("no `Scenario:` line")
        if problems:
            body = "\n".join(f"  - {p}" for p in problems)
            return f"FAIL — structural check only:\n{body}"
        return (
            "PASS — structural check only (gherkin-official is not installed). "
            "Full parse was NOT run."
        )

    async def _arun(self, document: str) -> str:
        """Async wrapper."""
        return self._run(document)

