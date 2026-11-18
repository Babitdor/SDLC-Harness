"""Mermaid model validator.

The gate @Diagram must pass before it may call a `.mmd` file done. Prefers the
Mermaid CLI (`mmdc`) when it is installed; otherwise falls back to a
deterministic structural check of the same failure classes the parser reports
(unknown header, unbalanced block, unlabelled edge, bad cardinality token).

The fallback is explicitly reported as a fallback: the agent is told the check
was weaker, never told a full parse passed.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

# First-line keyword → diagram family.
_HEADERS: dict[str, str] = {
    "sequenceDiagram": "sequence",
    "classDiagram": "class",
    "stateDiagram-v2": "state",
    "stateDiagram": "state",
    "erDiagram": "erd",
}

_CARDINALITY = ("||--o{", "||--|{", "}o--||", "|o--||", "}o--o{", "||--||")
_ARROWS = ("->>", "-->>", "->", "-->", "-x", "--x", "-)", "--)")
_HTML_TAG = re.compile(r"<[a-zA-Z/][^>]*>")


def _first_content_line(lines: list[str]) -> tuple[int, str]:
    """Return (0-based index, stripped line) of the first real content line."""
    for idx, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped and not stripped.startswith("%%"):
            return idx, stripped
    return -1, ""


class MermaidValidatorTool(BaseTool):
    """Validate a Mermaid diagram and report every problem it can see."""

    name: str = "mermaid-validator-tool"
    description: str = (
        "Validate a Mermaid diagram.\n"
        "Input: the complete .mmd file text (first line is the diagram "
        "keyword, e.g. `erDiagram`).\n"
        "Output: PASS plus how it was checked, or FAIL plus each problem and "
        "its line number.\n"
        "Use after every write to a diagrams/*.mmd file — this tool is the "
        'authoritative gate. A PASS that says "structural check only" means '
        "the Mermaid CLI is unavailable; report that limitation, do not hide it."
    )

    def _run(self, document: str) -> str:
        """Validate *document* and return a human-readable verdict."""
        mmdc = shutil.which("mmdc")
        if mmdc:
            verdict = self._run_mmdc(mmdc, document)
            if verdict is not None:
                return verdict
        return self._structural_check(document)

    def _run_mmdc(self, mmdc: str, document: str) -> str | None:
        """Return a verdict from the real Mermaid CLI, or None to fall back."""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "diagram.mmd"
            out = Path(tmp) / "diagram.svg"
            src.write_text(document, encoding="utf-8")
            try:
                proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
                    [mmdc, "-i", str(src), "-o", str(out)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                logger.warning("mmdc failed to run (%s) — structural fallback", exc)
                return None
        if proc.returncode == 0:
            return "PASS — validated by the Mermaid CLI (mmdc)."
        detail = (proc.stderr or proc.stdout or "").strip()
        return f"FAIL — mmdc rejected the diagram:\n{detail[:1500]}"

    def _structural_check(self, document: str) -> str:
        """Deterministic checks for the failure classes mmdc reports."""
        lines = document.splitlines()
        idx, header = _first_content_line(lines)
        if idx < 0:
            return "FAIL — the file is empty."

        family = _HEADERS.get(header)
        if family is None and (header.startswith("flowchart") or header.startswith("graph")):
            family = "flowchart"
        if family is None:
            return (
                f"FAIL — line {idx + 1}: unknown diagram header {header!r}. "
                "Expected one of: "
                f"{sorted(_HEADERS)}, `flowchart LR`, `graph TD`."
            )

        problems: list[str] = []
        open_blocks = 0
        for offset, raw in enumerate(lines[idx + 1 :], start=idx + 2):
            line = raw.strip()
            if not line or line.startswith("%%"):
                continue

            if _HTML_TAG.search(line):
                problems.append(f"line {offset}: HTML tag in a label")
            if line.count("(") != line.count(")"):
                problems.append(f"line {offset}: unbalanced parentheses")
            if line.count("[") != line.count("]"):
                problems.append(f"line {offset}: unbalanced brackets")

            if family == "flowchart":
                if line.startswith("subgraph"):
                    open_blocks += 1
                elif line == "end":
                    open_blocks -= 1
            elif family == "class":
                if line.endswith("{"):
                    open_blocks += 1
                elif line == "}":
                    open_blocks -= 1

            if family == "erd" and "--" in line:
                if not any(token in line for token in _CARDINALITY):
                    problems.append(
                        f"line {offset}: relationship has no valid cardinality token"
                    )
                if ":" not in line:
                    problems.append(f"line {offset}: relationship has no label")
            elif family in {"sequence", "state"}:
                # The initial/final pseudo-state transition is conventionally
                # unlabelled, so it is the one exemption from the label rule.
                if "[*]" in line:
                    continue
                if any(arrow in line for arrow in _ARROWS) and ":" not in line:
                    problems.append(f"line {offset}: edge has no label after ':'")

        if family == "state" and "[*]" not in document:
            problems.append("no initial state: [*] never appears")
        if open_blocks > 0:
            problems.append(f"{open_blocks} block(s) opened and never closed")
        if open_blocks < 0:
            problems.append(f"{-open_blocks} block(s) closed without being opened")

        if problems:
            body = "\n".join(f"  - {p}" for p in problems)
            return (
                f"FAIL — {len(problems)} structural issue(s) "
                f"(diagram type: {family}). Fix the file via edit_file and "
                f"re-validate:\n{body}"
            )

        return (
            f"PASS — structural check only (mmdc is not installed), "
            f"diagram type: {family}. Full Mermaid parse was NOT run."
        )

    async def _arun(self, document: str) -> str:
        """Async wrapper."""
        return self._run(document)

