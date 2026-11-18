"""OpenAPI 3.0 document validator.

The gate @API must pass before it may call design/openapi.yaml done. Uses
``openapi-spec-validator`` (openapi-spec-validator applies the official JSON
Schema plus the spec's own semantic rules) and degrades to a structural check
when that package is missing, so the agent is told the check was weaker rather
than being told a broken document passed.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

_HTTP_METHODS = {
    "get", "put", "post", "delete", "options", "head", "patch", "trace",
}


class OpenAPIValidatorTool(BaseTool):
    """Validate a full OpenAPI 3.0 document and report every error."""

    name: str = "openapi_validator_tool"
    description: str = (
        "Validate an OpenAPI 3.0 document.\n"
        "Input: the complete YAML (or JSON) document text.\n"
        "Output: PASS plus the detected version, or FAIL plus each error and "
        "where it sits.\n"
        "Use after every write to design/openapi.yaml — this tool is the "
        "authoritative gate."
    )

    def _run(self, document: str) -> str:
        """Validate *document* and return a human-readable verdict."""
        try:
            spec: Any = yaml.safe_load(document)
        except yaml.YAMLError as exc:
            return f"FAIL — YAML does not parse: {exc}"

        if not isinstance(spec, dict):
            return "FAIL — the document is not a YAML mapping."

        version = str(spec.get("openapi", ""))
        if not version.startswith("3."):
            return (
                'FAIL — missing or unsupported "openapi" version '
                f"(found {version!r}); use 3.0.x."
            )

        try:
            from openapi_spec_validator import validate
        except ImportError:
            logger.warning(
                "openapi-spec-validator not installed — falling back to a "
                "structural check",
            )
            return self._structural_check(spec, version)

        try:
            validate(spec)
        except Exception as exc:  # validator raises several error classes
            return f"FAIL — {type(exc).__name__}: {exc}"

        return f"PASS — valid OpenAPI {version} document."

    def _structural_check(self, spec: dict[str, Any], version: str) -> str:
        """Cheap fallback: required top-level keys and per-operation shape."""
        problems: list[str] = []
        if not isinstance(spec.get("info"), dict):
            problems.append("missing top-level `info` object")
        paths = spec.get("paths")
        if not isinstance(paths, dict) or not paths:
            problems.append("missing or empty top-level `paths` object")
        else:
            for path, item in paths.items():
                if not str(path).startswith("/"):
                    problems.append(f"path {path!r} does not start with /")
                if not isinstance(item, dict):
                    problems.append(f"path {path!r} is not a mapping")
                    continue
                operations = [k for k in item if k in _HTTP_METHODS]
                if not operations:
                    problems.append(f"path {path!r} declares no HTTP operation")
                for method in operations:
                    op = item[method]
                    if not isinstance(op, dict):
                        problems.append(f"{method.upper()} {path} is not a mapping")
                        continue
                    if not isinstance(op.get("responses"), dict):
                        problems.append(
                            f"{method.upper()} {path} declares no `responses`"
                        )

        if problems:
            body = "\n".join(f"  - {p}" for p in problems)
            return (
                "FAIL — structural check only (openapi-spec-validator is not "
                f"installed):\n{body}"
            )
        return (
            f"PASS — structural check only (openapi-spec-validator is not "
            f"installed), OpenAPI {version}. Full schema validation was NOT run."
        )

    async def _arun(self, document: str) -> str:
        """Async wrapper."""
        return self._run(document)

