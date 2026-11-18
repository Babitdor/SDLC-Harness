"""Artifact schemas and templates for the SDLC harness.

Each artifact is a structured markdown file that follows a defined schema.
These templates are injected into subagent system prompts so agents know
the exact format they must produce.

Also exposes ``EXPECTED_ARTIFACTS`` — the per-phase list of files the
orchestrator anticipates will exist by the end of a successful chat. This
is the single source of truth for the auto-regenerated ``index.md`` and
for the RQ1 phase-coverage metric.
"""

from __future__ import annotations

from typing import Literal

Phase = Literal["sources", "requirements", "design", "planning", "diagrams"]

# ── Artifact schemas (used in system prompts) ───────────────────────────
# Every schema is an OKF-frontmattered markdown template (or, for the
# machine-readable contracts, the file's own syntax). get_schema_prompt()
# injects {{timestamp}} / {{resource}} at render time.

REQUIREMENTS_SCHEMA = """
---
type: Requirements Document
title: Functional and Non-Functional Requirements
description: Verifiable requirements derived from the source material, each with a stable ID and a source reference.
tags: [requirements, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# Functional Requirements

REQ-001
<requirement text>
Source: <source file or user statement>

REQ-002
<requirement text>
Source: <source file or user statement>

# Non-Functional Requirements

REQ-NF-001
<requirement text>
Category: <performance | security | availability | usability | compliance>
Source: <source file or user statement>

## Rules:
- Each requirement gets a unique ID (REQ-NNN or REQ-NF-NNN). Never renumber an existing ID.
- One requirement per numbered item.
- Write requirements as verifiable statements ("The system shall ...").
- Every requirement cites its Source. If the source does not support it, do not write it.
"""

GLOSSARY_SCHEMA = """
---
type: Glossary
title: Domain Glossary
description: The vocabulary the source material uses, defined once so every downstream artifact means the same thing by it.
tags: [glossary, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# Glossary

| Term | Definition | Source |
|------|------------|--------|
| <Term> | <one-sentence definition> | <source> |

## Rules:
- One row per domain term.
- Define a term using the vocabulary the source uses, not a paraphrase of it.
- Do not invent terms the sources never use.
"""

CONSTRAINTS_SCHEMA = """
---
type: Constraints Document
title: Design Constraints
description: Quantifiable or verifiable constraints that bound the solution space, each with a source.
tags: [constraints, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# Constraints

C1: <constraint description>
  Type: <technical | budget | schedule | regulatory | operational>
  Source: <source>

C2: <constraint description>
  Type: <type>
  Source: <source>

## Rules:
- Each constraint gets a unique ID (C1, C2, ...).
- Constraints must be quantifiable or verifiable.
- Cite the source for every constraint.
"""

USER_STORIES_SCHEMA = """
---
type: User Stories
title: User Stories
description: Actor-centred stories that trace to requirements and are closed by acceptance criteria.
tags: [user-stories, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# Actors

- <Actor Name>

# User Stories

US-001: <story title>
  As a: <actor>
  I want: <capability>
  So that: <benefit>
  Traces to: REQ-NNN
  Acceptance: AC-NNN

## Rules:
- Each story gets a unique ID (US-NNN).
- Every story names exactly one actor and traces to at least one REQ ID.
- Do not restate a requirement verbatim — a story describes user value, a requirement describes system behaviour.
"""

ACCEPTANCE_CRITERIA_SCHEMA = """
---
type: Acceptance Criteria
title: Acceptance Criteria
description: Testable Given/When/Then criteria that close user stories and requirements.
tags: [acceptance-criteria, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# Acceptance Criteria

AC-001: <criterion title>
  Given: <precondition>
  When: <action>
  Then: <observable outcome>
  Verifies: REQ-NNN
  Test: TC-NNN

## Rules:
- Each criterion gets a unique ID (AC-NNN).
- Use Given/When/Then form with one observable outcome per criterion.
- Every AC references the requirement it verifies and must be mechanically testable.
"""

ARCHITECTURE_SCHEMA = """
---
type: Architecture Document
title: System Architecture
description: Component decomposition, data flow and quality-attribute targets, traceable to requirements.
tags: [architecture, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# System Context

<one paragraph: what the system does and who uses it>

# Components

| Component | Responsibility | Interfaces | Traces to |
|-----------|----------------|------------|-----------|
| <name>    | <single responsibility> | <interfaces> | REQ-NNN |

# Data Flow

1. <entry point>
2. <state change>
3. <output>

# Quality Attributes

- <attribute>: <target> (traces to REQ-NF-NNN)

# Risks and Open Questions

- <risk>

## Rules:
- Every component traces to at least one requirement.
- Exactly one responsibility per component.
- Do not bury technology choices here — record each one as an ADR in ADR.md.
"""

DATA_MODEL_SCHEMA = """
---
type: Data Model
title: Data Model
description: Entities, attributes and relationships backing the API and the persistence layer.
tags: [data-model, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# Entities

## <Entity>

- <attribute>: <type> — <constraint>
- Relationships: <relationship> to <Entity> (<cardinality>)

## Rules:
- Every entity has a primary identifier.
- Cardinality is explicit: 1, 0..1, 1..*, *.
- Every relationship references an entity defined in this document.
- Field names match the schemas in design/openapi.yaml.
"""

ADR_SCHEMA = """
---
type: Architecture Decision Record
title: Architecture Decision Records
description: One record per significant decision, with the forces, the choice and its consequences.
tags: [adr, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# ADR-001: <short decision title>

Status: <proposed | accepted | superseded by ADR-NNN>
Context: <the forces at play, traced to requirements>
Alternatives: <option considered — why it lost>
Decision: <what was chosen>
Consequences: <what becomes easier, what becomes harder>
Traces to: REQ-NNN

## Rules:
- Sequential IDs (ADR-NNN), never reused or renumbered.
- One decision per record.
- Consequences must name both the gain and the cost.
"""

API_SPEC_SCHEMA = """
---
type: API Specification
title: API Specification
description: Human-readable endpoint contract; the machine-readable twin is design/openapi.yaml.
tags: [api, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# Endpoints

## <METHOD> <path>

Purpose: <what it does>
Traces to: US-NNN
Request: <fields and types, or "none">
Response: <status code and shape>
Errors: <status code> — <condition>

## Rules:
- One section per endpoint.
- Every endpoint traces to a user story.
- Document at least one error response per endpoint.
- design/openapi.yaml MUST contain exactly these paths and operations — no more, no fewer.
"""

OPENAPI_SCHEMA = """
openapi: 3.0.3
info:
  title: <service name>
  version: <semver>
  description: <one line>
servers:
  - url: http://localhost:8000
paths:
  /<resource>:
    get:
      operationId: list<Resource>
      summary: <one line>
      responses:
        '200':
          description: <what is returned>
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/<Resource>'
        '500':
          description: <error condition>
components:
  schemas:
    <Resource>:
      type: object
      required: [<field>]
      properties:
        <field>:
          type: <string | integer | boolean | array | object>

## Rules:
- Valid OpenAPI 3.0.x. It MUST pass openapi_validator_tool with zero errors.
- The paths and operations here match design/API_SPEC.md exactly.
- Every response declares a schema or a $ref.
- No example values are required; do not invent response data.
"""

BACKLOG_SCHEMA = """
---
type: Backlog
title: Delivery Backlog
description: Epics and ordered work items traceable to user stories.
tags: [backlog, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# Epics

## EP-001: <epic name>

Traces to: REQ-NNN

# Items

| ID | Item | Epic | Priority | Estimate | Depends on | Traces to |
|----|------|------|----------|----------|------------|-----------|
| BI-001 | <task> | EP-001 | P1 | S | — | US-NNN |

## Rules:
- Every item has a unique ID (BI-NNN) and belongs to exactly one epic.
- Priority is P0..P3; estimate is relative size (XS, S, M, L, XL).
- Every item traces to a user story or requirement.
- Order items so that no item depends on a later one.
"""

TEST_PLAN_SCHEMA = """
---
type: Test Plan
title: Test Plan
description: Test levels, cases and coverage gaps closing the acceptance criteria.
tags: [test-plan, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# Strategy

- **unit** — <what it covers>
- **integration** — <what it covers>
- **contract** — <what it covers>
- **end-to-end** — <what it covers>

# Test Cases

## TC-001: <title>

Level: <unit | integration | contract | e2e>
Verifies: AC-NNN
Given / When / Then: <one line each>
Expected result: <observable outcome>

# Coverage Gaps

- <AC-NNN has no automated test yet>

## Rules:
- Every TC traces to an acceptance criterion (AC-NNN).
- Every criterion in ACCEPTANCE_CRITERIA.md is covered by at least one TC.
- List uncovered criteria under Coverage Gaps rather than omitting them.
"""

CI_CD_SCHEMA = """
---
type: CI/CD Pipeline
title: CI/CD Design
description: Stages, triggers, gates and environments; the executable twin is planning/ci/pipeline.yml.
tags: [ci-cd, sdlc]
timestamp: {{timestamp}}
resource: {{resource}}
---

# Stages

| Stage | Trigger | Steps | Gate |
|-------|---------|-------|------|
| build | push | <steps> | <condition> |

# Environments

- <name>: <purpose>

# Secrets and Permissions

- <secret name>: <where it comes from>

## Rules:
- Every stage names its trigger and its gate condition.
- List secret NAMES only — never a value.
- planning/ci/pipeline.yml MUST implement exactly these stages, in this order.
"""

CI_PIPELINE_SCHEMA = """
name: ci

on:
  push:
    branches: [main]
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: <step name>
        run: <command>

## Rules:
- Valid GitHub Actions YAML. It MUST pass ci_pipeline_validator_tool with zero errors.
- Every job declares runs-on and at least one step.
- Every step is either "uses:" or "run:" — never both.
- The stages here match planning/CI_CD.md exactly.
"""

MERMAID_SEQUENCE_SCHEMA = """
sequenceDiagram
    autonumber
    actor User
    participant API
    participant Service
    User->>API: <request>
    API->>Service: <call>
    Service-->>API: <result>
    API-->>User: <response>

## Rules:
- The first line is exactly "sequenceDiagram".
- Declare every participant with actor/participant before using it.
- Every arrow carries a label after ":".
- No HTML tags and no parentheses inside labels.
"""

MERMAID_CLASS_SCHEMA = """
classDiagram
    class Order {
        +String id
        +place() bool
    }
    class LineItem {
        +String sku
        +int quantity
    }
    Order "1" --> "*" LineItem : contains

## Rules:
- The first line is exactly "classDiagram".
- Declare members inside a class block; "+" public, "-" private.
- Every relationship has quoted cardinality and a label.
- Class names match the entities in design/DATA_MODEL.md.
"""

MERMAID_STATE_SCHEMA = """
stateDiagram-v2
    [*] --> Draft
    Draft --> Submitted : submit
    Submitted --> Draft : reject
    Submitted --> [*] : approve

## Rules:
- The first line is exactly "stateDiagram-v2".
- Begin at [*] and end at least one path at [*].
- Every transition carries a label after ":".
- Every non-initial state is reachable from the initial state.
"""

MERMAID_ERD_SCHEMA = """
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains

## Rules:
- The first line is exactly "erDiagram".
- Cardinality tokens are limited to ||--o{, ||--|{, }o--||, |o--||.
- Every relationship carries a label after ":".
- Entities match design/DATA_MODEL.md.
"""

MERMAID_DEPLOYMENT_SCHEMA = """
flowchart LR
    subgraph edge[Edge]
        LB[Load balancer]
    end
    subgraph app[Application]
        API[API service]
    end
    LB -->|HTTPS| API

## Rules:
- Mermaid has no native deployment diagram: use "flowchart LR" with one subgraph per deployment node.
- Every subgraph declares a display label with [label].
- Every edge is labelled with the protocol.
- Node names match the components in design/ARCHITECTURE.md.
"""

# ── Mapping: artifact name → its schema ─────────────────────────────────

ARTIFACT_SCHEMAS: dict[str, str] = {
    "REQUIREMENTS.md": REQUIREMENTS_SCHEMA,
    "GLOSSARY.md": GLOSSARY_SCHEMA,
    "CONSTRAINTS.md": CONSTRAINTS_SCHEMA,
    "USER_STORIES.md": USER_STORIES_SCHEMA,
    "ACCEPTANCE_CRITERIA.md": ACCEPTANCE_CRITERIA_SCHEMA,
    "ARCHITECTURE.md": ARCHITECTURE_SCHEMA,
    "DATA_MODEL.md": DATA_MODEL_SCHEMA,
    "ADR.md": ADR_SCHEMA,
    "API_SPEC.md": API_SPEC_SCHEMA,
    "openapi.yaml": OPENAPI_SCHEMA,
    "BACKLOG.md": BACKLOG_SCHEMA,
    "TEST_PLAN.md": TEST_PLAN_SCHEMA,
    "CI_CD.md": CI_CD_SCHEMA,
    "ci/pipeline.yml": CI_PIPELINE_SCHEMA,
    "sequence.mmd": MERMAID_SEQUENCE_SCHEMA,
    "class.mmd": MERMAID_CLASS_SCHEMA,
    "state.mmd": MERMAID_STATE_SCHEMA,
    "erd.mmd": MERMAID_ERD_SCHEMA,
    "deployment.mmd": MERMAID_DEPLOYMENT_SCHEMA,
}


def get_schema_prompt(
    artifact_name: str,
    timestamp: str | None = None,
    project_id: str | None = None,
) -> str:
    """Return a brief instruction string telling the agent to follow a schema.

    Parameters
    ----------
    artifact_name:
        The artifact filename (e.g. ``REQUIREMENTS.md``).
    timestamp:
        ISO-8601 timestamp to inject into the schema's ``{{timestamp}}``
        placeholder. Defaults to the current UTC time.
    project_id:
        When supplied, the OKF ``resource`` field is injected with the
        artifact's stable read-endpoint path
        (``/projects/<id>/artifacts/<name>``). When ``None`` — the usual case,
        since subagent prompts are built once at import time with no project
        context — ``resource`` falls back to the artifact's workspace-relative
        bundle path (the same target ``index.md`` links use), which is portable
        and project-agnostic.
    """
    schema = ARTIFACT_SCHEMAS.get(artifact_name)
    if not schema:
        return ""
    if timestamp is None:
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rendered = schema.replace("{{timestamp}}", timestamp)
    if project_id:
        resource = f"/projects/{project_id}/artifacts/{artifact_name}"
    else:
        resource = _bundle_path_for(artifact_name)
    rendered = rendered.replace("{{resource}}", resource)
    return (
        f"\n\nYou MUST produce the artifact `{artifact_name}` following this "
        f"schema exactly:\n\n{rendered}"
    )


# ── Expected artifacts per phase ────────────────────────────────────────
#
# Used by the auto-regenerated `index.md` (workspace-side) and by the
# artifact-listing endpoint to render phase-grouped completeness. Paths are
# given RELATIVE to each phase folder (e.g. `REQUIREMENTS.md` lives at
# `requirements/REQUIREMENTS.md` inside the workspace root).
#
# `sources/` has no expected files — its contents are entirely user-driven
# (uploads + ingestion-extracted markdown).
#
# The catalogue stops at specs: validated OpenAPI, a CI pipeline definition and
# Mermaid models. Nothing here claims a working implementation was produced.

# Project-root bookkeeping files that live at the workspace root, NOT under
# a phase folder. `log.md` is written to `{root}/log.md` (see
# ProjectWorkspace.init_directories / append_log), so listing it as
# `sources/log.md` made the artifact endpoint 404 on click. `index.md`
# is intentionally excluded — it's a self-referential auto-index that
# scan_workspace_files already filters out.
ROOT_ARTIFACTS: list[str] = ["log.md"]

EXPECTED_ARTIFACTS: dict[Phase, list[str]] = {
    "sources": [],
    "requirements": [
        "REQUIREMENTS.md",
        "GLOSSARY.md",
        "CONSTRAINTS.md",
        "USER_STORIES.md",
        "ACCEPTANCE_CRITERIA.md",
    ],
    "design": [
        "ARCHITECTURE.md",
        "DATA_MODEL.md",
        "ADR.md",
        "API_SPEC.md",
        "openapi.yaml",
    ],
    "planning": [
        "BACKLOG.md",
        "TEST_PLAN.md",
        "CI_CD.md",
        "ci/pipeline.yml",
    ],
    "diagrams": [
        "sequence.mmd",
        "class.mmd",
        "state.mmd",
        "erd.mmd",
        "deployment.mmd",
    ],
}


def _bundle_path_for(artifact_name: str) -> str:
    """Return the workspace-relative bundle path for an artifact name.

    Maps a schema key (e.g. ``REQUIREMENTS.md`` or ``ci/pipeline.yml``) to its
    phase-qualified location (``requirements/REQUIREMENTS.md``,
    ``planning/ci/pipeline.yml``) using ``EXPECTED_ARTIFACTS``. Falls back to
    the name unchanged when it is not in the expected catalogue.
    """
    for phase, files in EXPECTED_ARTIFACTS.items():
        for f in files:
            if f == artifact_name:
                return f"{phase}/{f}"
    return artifact_name


def expected_artifact_paths() -> list[str]:
    """Return every expected artifact as a workspace-relative path.

    Example: ``["requirements/REQUIREMENTS.md", "logical/BDD.md", ...]``.
    Used by the artifact-listing endpoint to issue a single batched
    existence-check inside the Docker container.
    """
    out: list[str] = []
    for phase, files in EXPECTED_ARTIFACTS.items():
        for f in files:
            out.append(f"{phase}/{f}")
    return out


# ── Auto-regenerated index.md ───────────────────────────────────────────
#
# The artifact-listing endpoint batches a stat call for every expected
# artifact, builds a dict[path → (size, mtime)], and on every detected change
# calls build_index_md() + writes it to /workspace/project_<id>/index.md.

_PHASE_TITLES: dict[Phase, str] = {
    "sources": "Sources",
    "requirements": "Requirements phase",
    "design": "Design phase",
    "planning": "Planning phase",
    "diagrams": "Diagrams phase",
}


def _format_size(size_bytes: int) -> str:
    """Human-readable file size for the index."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _extract_frontmatter_type(content: str) -> str | None:
    """Extract the ``type`` field from YAML frontmatter, if present.

    Returns the type value (e.g. ``"Requirements Document"``) or ``None``
    if no frontmatter or no type field is found.
    """
    if not content.startswith("---"):
        return None
    end = content.find("---", 3)
    if end == -1:
        return None
    for line in content[3:end].strip().splitlines():
        line = line.strip()
        if line.startswith("type:"):
            val = line[5:].strip().strip('"').strip("'")
            return val if val else None
    return None


def build_index_md(
    project_id: str,
    files_info: dict[str, tuple[int, int]],
    types: dict[str, str] | None = None,
) -> str:
    """Render the ``index.md`` body for one project workspace.

    Parameters
    ----------
    project_id:
        Used in the header.
    files_info:
        Maps workspace-relative path (e.g. ``requirements/REQUIREMENTS.md``)
        to ``(byte_size, mtime_epoch_seconds)``. Includes every file in
        the workspace except index.md / metadata/ / .keep seeds.

    Layout per phase:
      1. Each artifact in EXPECTED_ARTIFACTS — ticked [x] when present,
         [ ] when not yet produced.
      2. Any *other* files found in that phase folder (created by an
         agent or the user outside the expected catalogue) are listed
         under "Other files".

    The ``sources/`` phase has no expected entries, so its section
    contains only an "Other files" listing (the raw uploads).
    """
    from datetime import datetime, timezone

    types = types or {}

    def _fmt(rel: str) -> str:
        size, mtime = files_info[rel]
        ts = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
        meta = f"{_format_size(size)}, {ts}"
        artifact_type = types.get(rel)
        if artifact_type:
            return f"*{artifact_type}* · {meta}"
        return meta

    expected = set(expected_artifact_paths())
    produced_expected = sum(1 for p in expected if p in files_info)
    total_expected = len(expected)
    total_files = len(files_info)

    lines: list[str] = [f"# Project workspace — {project_id}", ""]
    lines.append(
        f"**Coverage:** {produced_expected} / {total_expected} expected artifacts produced "
        f"· **{total_files} file(s)** in workspace."
    )
    lines.append("")

    for phase, files in EXPECTED_ARTIFACTS.items():
        # Files actually on disk that live in this phase folder.
        in_phase = {
            rel: info
            for rel, info in files_info.items()
            if rel.startswith(f"{phase}/")
        }
        # Names the orchestrator expects for this phase.
        expected_relset = {f"{phase}/{f}" for f in files}

        # Skip empty phases entirely — keeps the index tight before agents
        # have done any work for that phase.
        if not files and not in_phase:
            continue

        lines.append(f"## {_PHASE_TITLES[phase]}")

        # 1. Expected artifacts — always rendered, ticked or pending.
        for f in files:
            rel = f"{phase}/{f}"
            display = f.rsplit("/", 1)[-1]
            if rel in files_info:
                lines.append(f"- [x] [{display}]({rel}) — {_fmt(rel)}")
            else:
                lines.append(f"- [ ] {display} — *not yet produced*")

        # 2. Any other files in this phase folder.
        extras = sorted(rel for rel in in_phase if rel not in expected_relset)
        if extras:
            if files:  # divider only when we already listed expected entries
                lines.append("")
            lines.append("**Other files:**")
            for rel in extras:
                # Strip the phase prefix for display, keep full path in the link.
                display = rel[len(phase) + 1 :]
                lines.append(f"- [{display}]({rel}) — {_fmt(rel)}")
        lines.append("")
    return "\n".join(lines)


async def scan_workspace_files(ws) -> dict[str, tuple[int, int]]:
    """Walk a project workspace and return ``{rel_path: (size, mtime)}``.

    Single source of truth for the workspace file inventory — shared by the
    artifact-listing endpoint (change detection + index regen) and the
    chat-stream path (before/after diffing for log.md + lineage). Excludes
    ``index.md`` (self-reference), ``metadata/*`` (bookkeeping), and ``.keep``
    seed files, exactly mirroring the listing endpoint's historical behaviour.

    ``ws`` is typed loosely to avoid a circular import with
    ``workspace.ProjectWorkspace``.
    """
    find_cmd = (
        f"find {ws.root} -mindepth 1 -type f "
        "-not -name 'index.md' "
        "-not -path '*/metadata/*' "
        "-not -name '.keep' "
        "-printf '%P|%s|%T@\\n' 2>/dev/null"
    )
    result = await ws.backend.execute_async(find_cmd)

    files_info: dict[str, tuple[int, int]] = {}
    for line in result.output.strip().splitlines():
        parts = line.split("|")
        if len(parts) != 3:
            continue
        rel, size_str, mtime_str = parts
        try:
            files_info[rel] = (int(size_str), int(float(mtime_str)))
        except ValueError:
            continue
    return files_info


async def _read_frontmatter_types(ws, files_info: dict[str, tuple[int, int]]) -> dict[str, str]:
    """Return ``{rel_path: type}`` for present markdown artifacts.

    Reads only the leading bytes of each ``.md`` file (enough to cover the YAML
    frontmatter block) and runs ``_extract_frontmatter_type``. Non-markdown
    files are skipped — they keep the plain size+mtime index line.
    """
    md_paths = [rel for rel in files_info if rel.endswith(".md")]
    types: dict[str, str] = {}
    for rel in md_paths:
        result = await ws.backend.execute_async(f"head -c 600 {ws.root}/{rel} 2>/dev/null")
        t = _extract_frontmatter_type(result.output)
        if t:
            types[rel] = t
    return types


async def regenerate_index(
    ws,
    files_info: dict[str, tuple[int, int]],
    types: dict[str, str] | None = None,
) -> None:
    """Write a freshly composed ``index.md`` into the workspace root.

    Idempotent and cheap — one ``cat > ... <<EOF`` exec per call. Should
    be invoked only when ``files_info`` has changed since the last write
    (mtime-based change detection lives in the listing endpoint).

    When ``types`` is not supplied, the OKF ``type`` of each present markdown
    artifact is read from its frontmatter so the index can surface it.

    ``ws`` is typed loosely (``Any``) to avoid a circular import with
    ``workspace.ProjectWorkspace``.
    """
    if types is None:
        types = await _read_frontmatter_types(ws, files_info)
    content = build_index_md(ws.project_id, files_info, types)
    # Single-quoted heredoc — shell does not interpolate inside it, so we
    # don't need to escape `$`, backticks, or backslashes.
    cmd = (
        f"cat > {ws.root}/index.md << 'SDLC_INDEX_EOF'\n"
        f"{content}\n"
        f"SDLC_INDEX_EOF"
    )
    await ws.backend.execute_async(cmd)