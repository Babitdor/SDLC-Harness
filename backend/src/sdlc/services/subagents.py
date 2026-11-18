"""SDLC subagent definitions and tool wiring.

Agent roster:
  - @Ingestion     → raw input → REQUIREMENTS.md, GLOSSARY.md, CONSTRAINTS.md
  - @Requirements  → requirements → USER_STORIES.md, ACCEPTANCE_CRITERIA.md
  - @Architecture  → requirements → ARCHITECTURE.md, DATA_MODEL.md, ADR.md
  - @API           → stories + data model → API_SPEC.md + validated openapi.yaml
  - @Planning      → stories + criteria → BACKLOG.md, TEST_PLAN.md
  - @DevOps        → test plan → CI_CD.md + validated ci/pipeline.yml
  - @Diagram       → design artifacts → ONE validated Mermaid model per invocation

All agent communication goes through structured markdown artifacts organised
into wiki-style phase folders under /workspace/project_<id>/ (sources/,
requirements/, design/, planning/, diagrams/). The orchestrator resolves the
dependency DAG automatically when a downstream agent is invoked.

The pipeline stops at specs: validated OpenAPI, a validated CI pipeline file and
validated Mermaid models. No agent claims to have produced runnable software.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain.agents.middleware import ModelRetryMiddleware

from sdlc.core.config import AGENT_IDENTITY
from sdlc.services.artifacts import get_schema_prompt
from sdlc.services.caveman import caveman_middleware, recovery_tools

logger = logging.getLogger(__name__)

# ── Skills base directory ─────────────────────────────────────────────────
# Host path to skill files, mounted as /skills/ in the backend.
SKILLS_HOST_DIR = Path(__file__).resolve().parent.parent / "skills"

# Backend path prefix where skills are accessible.
_SKILLS_BACKEND_PREFIX = "/skills"


# ── Prompt renderer ──────────────────────────────────────────────────────

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_JINJA_ENV = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))

# Schema variables injected into templates. Lazily computed per artifact name
# so that missing optional dependencies do not crash at import time.
_SCHEMA_VARS: dict[str, str] = {}


def _schema_var(name: str) -> str:
    """Return the rendered schema prompt for *name*, cached."""
    if name not in _SCHEMA_VARS:
        _SCHEMA_VARS[name] = get_schema_prompt(name)
    return _SCHEMA_VARS[name]


def _render_prompt(template_name: str, **extra_vars: str) -> str:
    """Load and render a Jinja2 prompt template with schema variables."""
    template = _JINJA_ENV.get_template(template_name)
    return template.render(**extra_vars)


def _retry_middleware() -> list[Any]:
    """The middleware every subagent shares: retry, and read less.

    Caveman sits here rather than in each subagent spec for the same reason
    retry does: one list, seven agents, and a new subagent inherits both
    without anyone remembering to add them. It compacts tool *results* on
    their way into that agent's context; it never touches the artifacts the
    agent writes.
    """
    return [
        ModelRetryMiddleware(
            max_retries=3,
            backoff_factor=2.0,
            initial_delay=1.0,
        ),
        *caveman_middleware(),
    ]


def _build_tools() -> dict[str, list]:
    """Instantiate domain-specific validator tools for subagents.

    Returns a dict mapping subagent name → list of BaseTool instances.
    Tools whose dependencies are missing are silently skipped with a
    warning so the rest of the system stays functional.
    """
    tools: dict[str, list] = {
        "diagram": [],
        "api": [],
        "planning": [],
        "devops": [],
    }

    # ── Mermaid tools (@Diagram) ───────────────────────────────────────
    try:
        from sdlc.tools.MermaidValidatorTool import MermaidValidatorTool

        tools["diagram"].append(MermaidValidatorTool())
    except ImportError as exc:
        logger.warning("MermaidValidatorTool unavailable: %s", exc)

    try:
        from sdlc.tools.MermaidSyntaxTool import MermaidSyntaxTool

        tools["diagram"].append(MermaidSyntaxTool())
    except ImportError as exc:
        logger.warning("MermaidSyntaxTool unavailable: %s", exc)

    # ── OpenAPI tool (@API) ────────────────────────────────────────────
    try:
        from sdlc.tools.OpenAPIValidatorTool import OpenAPIValidatorTool

        tools["api"].append(OpenAPIValidatorTool())
    except ImportError as exc:
        logger.warning("OpenAPIValidatorTool unavailable: %s", exc)

    # ── Gherkin tool (@Planning) ───────────────────────────────────────
    try:
        from sdlc.tools.GherkinValidatorTool import GherkinValidatorTool

        tools["planning"].append(GherkinValidatorTool())
    except ImportError as exc:
        logger.warning("GherkinValidatorTool unavailable: %s", exc)

    # ── CI pipeline tool (@DevOps) ─────────────────────────────────────
    try:
        from sdlc.tools.CiPipelineValidatorTool import CiPipelineValidatorTool

        tools["devops"].append(CiPipelineValidatorTool())
    except ImportError as exc:
        logger.warning("CiPipelineValidatorTool unavailable: %s", exc)

    # ── MCP tools (user-configured servers) ────────────────────────────
    # services/mcp.py loads them into a cache at startup and after every
    # settings change. create_orchestrator() is synchronous, so this is a
    # cache read; an empty cache simply means "no MCP tools configured".
    try:
        from sdlc.services import mcp as mcp_client

        for agent_name, extra_tools in mcp_client.tools_for_all().items():
            tools.setdefault(agent_name, []).extend(extra_tools)
    except Exception as exc:  # noqa: BLE001 - never break agent creation
        logger.warning("MCP tools unavailable: %s", exc)

    return tools


# ── Orchestrator-level tools ─────────────────────────────────────────────
#
# Tools attached directly to the orchestrator (not to any subagent). The
# orchestrator is the only place where external information (web search)
# is appropriate — subagents must stay deterministic and traceable to the
# structured artifacts that flow through /workspace/project_*/.


def _build_orchestrator_tools() -> list[Any]:
    """Build the orchestrator's domain-tool list.

    Returns an empty list when optional deps are missing so the backend
    boots cleanly on stripped environments. Each builder logs its own
    "loaded N tools" / "unavailable" line.
    """
    tools: list[Any] = []

    # 1. Ask clarifying question tool
    try:
        from sdlc.tools.AskQuestionTool import build_ask_question_tools

        tools.extend(build_ask_question_tools())
    except Exception as exc:
        logger.warning("AskQuestionTool unavailable: %s", exc)

    # 2. Web search tool
    try:
        from sdlc.tools.WebSearchTool import build_web_search_tools

        tools.extend(build_web_search_tools())
    except ImportError as exc:
        logger.warning("WebSearchTool unavailable (missing dependency): %s", exc)

    return tools


# ── Subagent definitions ────────────────────────────────────────────────

INGESTION_AGENT: dict[str, Any] = {
    "name": "ingestion",
    "description": (
        "Ingestion agent. Converts raw input files (PDF, XLSX, DOCX, text) "
        "into structured markdown artifacts: REQUIREMENTS.md, GLOSSARY.md, "
        "CONSTRAINTS.md. Requires user-provided input — will NOT fabricate "
        "content. Invoke with @Ingestion."
    ),
    "system_prompt": _render_prompt(
        "ingestion.j2",
        schema_requirements=_schema_var("REQUIREMENTS.md"),
        schema_glossary=_schema_var("GLOSSARY.md"),
        schema_constraints=_schema_var("CONSTRAINTS.md"),
    ),
    "middleware": _retry_middleware(),
}

REQUIREMENTS_AGENT: dict[str, Any] = {
    "name": "requirements",
    "description": (
        "Requirements agent. Derives actor-centred user stories and their "
        "Given/When/Then acceptance criteria from REQUIREMENTS.md. Requires "
        "@Ingestion to have produced REQUIREMENTS.md. Invoke with "
        "@Requirements. Does NOT design solutions or pick technology."
    ),
    "system_prompt": _render_prompt(
        "requirements.j2",
        schema_user_stories=_schema_var("USER_STORIES.md"),
        schema_acceptance_criteria=_schema_var("ACCEPTANCE_CRITERIA.md"),
    ),
    "middleware": _retry_middleware(),
}

ARCHITECTURE_AGENT: dict[str, Any] = {
    "name": "architecture",
    "description": (
        "Architecture agent. Produces the component decomposition, the data "
        "model and the decision records (ARCHITECTURE.md, DATA_MODEL.md, "
        "ADR.md) from requirements and constraints. Requires REQUIREMENTS.md "
        "and CONSTRAINTS.md. Invoke with @Architecture."
    ),
    "system_prompt": _render_prompt(
        "architecture.j2",
        schema_architecture=_schema_var("ARCHITECTURE.md"),
        schema_data_model=_schema_var("DATA_MODEL.md"),
        schema_adr=_schema_var("ADR.md"),
    ),
    "middleware": _retry_middleware(),
}

API_AGENT: dict[str, Any] = {
    "name": "api",
    "description": (
        "API agent. Produces the human-readable endpoint contract "
        "(design/API_SPEC.md) and its machine-readable twin "
        "(design/openapi.yaml), validated to zero errors with "
        "openapi_validator_tool. Requires USER_STORIES.md and "
        "DATA_MODEL.md. Invoke with @API."
    ),
    "system_prompt": _render_prompt(
        "api.j2",
        schema_api_spec=_schema_var("API_SPEC.md"),
        schema_openapi=_schema_var("openapi.yaml"),
    ),
    "middleware": _retry_middleware(),
}

PLANNING_AGENT: dict[str, Any] = {
    "name": "planning",
    "description": (
        "Planning agent. Turns stories and acceptance criteria into an "
        "ordered delivery backlog (BACKLOG.md) and a test plan "
        "(TEST_PLAN.md) whose cases close every acceptance criterion. "
        "Requires USER_STORIES.md and ACCEPTANCE_CRITERIA.md. Invoke with "
        "@Planning."
    ),
    "system_prompt": _render_prompt(
        "planning.j2",
        schema_backlog=_schema_var("BACKLOG.md"),
        schema_test_plan=_schema_var("TEST_PLAN.md"),
    ),
    "middleware": _retry_middleware(),
}

DEVOPS_AGENT: dict[str, Any] = {
    "name": "devops",
    "description": (
        "DevOps agent. Designs the CI/CD stages (planning/CI_CD.md) and the "
        "executable GitHub Actions pipeline (planning/ci/pipeline.yml), "
        "validated to zero errors with ci_pipeline_validator_tool. Requires "
        "TEST_PLAN.md. Invoke with @DevOps."
    ),
    "system_prompt": _render_prompt(
        "devops.j2",
        schema_ci_cd=_schema_var("CI_CD.md"),
        schema_pipeline=_schema_var("ci/pipeline.yml"),
    ),
    "middleware": _retry_middleware(),
}

DIAGRAM_AGENT: dict[str, Any] = {
    "name": "diagram",
    "description": (
        "Diagram agent. Produces exactly ONE validated Mermaid model per "
        "invocation. The orchestrator passes diagram_type, input_path, "
        "output_path, skill_path and diagram_name in the task description. "
        "Has syntax-reference and validation tools. Requires the upstream "
        "artifacts named for that diagram_type. Invoke with @Diagram."
    ),
    # SkillsMiddleware enumerates subdirectories of this path looking for
    # SKILL.md files. Pointing at individual skill directories breaks
    # discovery (the middleware then sees a SKILL.md as a file, not a
    # skill-bearing subdirectory, and loads zero skills).
    "skills": ["/skills"],
    "system_prompt": _render_prompt(
        "diagram.j2",
        schema_sequence=_schema_var("sequence.mmd"),
        schema_class=_schema_var("class.mmd"),
        schema_state=_schema_var("state.mmd"),
        schema_erd=_schema_var("erd.mmd"),
        schema_deployment=_schema_var("deployment.mmd"),
    ),
    "middleware": _retry_middleware(),
    # "tools" is injected at orchestrator creation time by attach_tools()
}

ALL_SUBAGENTS: list[dict[str, Any]] = [
    INGESTION_AGENT,
    REQUIREMENTS_AGENT,
    ARCHITECTURE_AGENT,
    API_AGENT,
    PLANNING_AGENT,
    DEVOPS_AGENT,
    DIAGRAM_AGENT,
]

# ── Orchestrator system prompt ───────────────────────────────────────────

ORCHESTRATOR_PROMPT = _render_prompt("orchestrator.j2", agent_identity=AGENT_IDENTITY)


# ── Tool attachment ──────────────────────────────────────────────────────


def attach_tools(
    subagents: list[dict[str, Any]], tools_map: dict[str, list]
) -> list[dict[str, Any]]:
    """Attach domain-specific tools to subagent specs that declare them.

    Iterates over the subagent list and, for any agent whose name appears
    in *tools_map*, sets the ``"tools"`` key.  This is done at orchestrator
    creation time (not at module level) so that missing optional
    dependencies are handled gracefully.
    """
    result: list[dict[str, Any]] = []
    for spec in subagents:
        name = spec["name"]
        # caveman_retrieve goes to every agent, domain capability or not: any
        # agent whose tool results got compacted needs a way to read them back.
        agent_tools = [*tools_map.get(name, []), *recovery_tools()]
        if agent_tools:
            # Shallow-copy so we don't mutate the module-level constant.
            spec = {**spec, "tools": agent_tools}
            logger.info(
                "Attached %d tool(s) to subagent '%s': %s",
                len(agent_tools),
                name,
                [t.name for t in agent_tools],
            )
        result.append(spec)
    return result

