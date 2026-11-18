# SDLC Harness

A multi-agent orchestrator that turns a rough product brief into a traceable specification set. Seven specialist agents communicate through structured markdown artifacts inside an isolated per-chat Docker sandbox, organised by delivery phase (sources / requirements / design / planning / diagrams). The orchestrator resolves the dependency DAG automatically and consults a wiki-style auto-regenerated `index.md` for quick state lookups. Full LangSmith tracing for observability.

The pipeline stops at specs: a validated OpenAPI document, a validated CI pipeline file and validated Mermaid models. No agent claims to have produced runnable software.

**Runtime-tunable model settings** — swap the LLM endpoint, API key, agent model, or vision model from the Settings panel without editing `.env` or restarting the server. Changes take effect on the next chat session.

**MCP provider authentication** — connect external tool servers with OAuth, bearer tokens or API keys from the MCP panel. See [setup and credential handling](MCP_AUTH.md).

---

## Architecture

![SDLC Harness — multi-agent architecture with Docker-sandboxed unified state](assets/Architecture.png)

Four layers, top to bottom:

- **Chat UI → FastAPI → Orchestrator** — Next.js front-end streams over SSE; the FastAPI backend dispatches to a LangGraph orchestrator with `web_search` (DuckDuckGo) plus a `task` tool for sub-agent delegation. Every LLM call, tool use, and DAG hop is traced into LangSmith.
- **Agent layer** — seven specialist sub-agents, one per delivery phase. Each owns a fixed set of output artifacts (see the roster below). Subagents run in-process (blocking) and share the same per-chat Docker sandbox container.
- **Unified state (Docker sandbox)** — one container per chat thread. All agents read and write the same `/workspace/project_<id>/` tree organised into `sources/`, `requirements/`, `design/`, `planning/`, `diagrams/`, and `skills/`. The skills directory is bind-mounted so `@Diagram`'s Phase C `LEARNED.md` appends survive image rebuilds.
- **Infrastructure** — Postgres for conversation persistence, SQLite for LangGraph checkpoints, and an OpenAI-compatible LLM gateway (NHR FAU by default).

Auto-regenerated `index.md` at the workspace root is the orchestrator's single quick-lookup view — every expected artifact ticked ready or pending, refreshed on mtime change.

---

## Features

### Backend

| Feature | Description |
|---|---|
| **SSE Streaming** | Multi-subscriber `RunContext` with history replay and live tail. Supports resume — a re-attaching consumer catches up via snapshot replay, then tails live events. |
| **LangGraph Orchestrator** | Compiled deep-agent with 7 subagents, dependency DAG resolution, and automatic artifact routing. |
| **Postgres Persistence** | Async SQLAlchemy + asyncpg + Alembic migrations for conversations and messages. JSONB columns for tool calls and attachments. |
| **SQLite Checkpointer** | Per-thread conversation memory via `AsyncSqliteSaver` — survives server restarts. |
| **LangSmith Tracing** | Every LLM call, tool use, and DAG hop tagged with `project_id` / `thread_id`. Connectivity check at startup with timeout. |
| **Orchestrator Identity** | The orchestrator introduces itself by name (`AGENT_IDENTITY`, default **DevForge**) in its system prompt — a senior SDLC orchestrator coordinating the end-to-end spec pipeline. |
| **Mermaid Validation** | Parses generated Mermaid models and reports syntax errors back to `@Diagram` for repair. |
| **Mermaid Syntax Reference** | Exact Mermaid v2 syntax for every supported diagram type. |
| **OpenAPI Validation** | Parses `openapi.yaml` and rejects a contract the spec generator cannot round-trip. |
| **Gherkin Validation** | Parses the feature files a test plan references, so scenarios stay executable. |
| **CI Pipeline Validation** | Parses `ci/pipeline.yml` against its expected shape before the harness reports it ready. |
| **Ask User** | Structured clarifying question tool (`AskQuestionTool`) so an agent can stop and ask instead of guessing. |
| **Web Search** | DuckDuckGo search for grounding orchestrator decisions. |
| **File Upload** | Multi-file upload with filename sanitisation, direct-to-container transfer. |
| **Binary Preview** | DOCX (mammoth), PDF (PyMuPDF), XLSX (openpyxl) → styled HTML for in-browser preview. |
| **Markdown → PDF** | Download any markdown artifact as a PDF. |
| **HITL Approval** | Human-in-the-loop gating for `write_file` / `edit_file` with approve/reject/edit workflow. |
| **ShellGuard** | Deterministic safety middleware that hard-blocks destructive shell commands (`rm -rf`, `chmod`, `sudo`, etc.). |
| **Custom Subagents** | User-created agents stored in `custom_agents.json`, merged into the orchestrator roster at runtime. Reserved names protected. |
| **Runtime Model Settings** | Swap LLM endpoint, API key, agent model, and vision model from the UI — no `.env` edit or restart needed. Stored overrides cascade over env vars. |
| **Auto-regenerated index.md** | Mtime-based change detection — rewrites `index.md` only when files change. |
| **Artifact Cache** | Short-TTL cache (default 1s) for artifact list polling — cuts Docker exec calls ~50%. |
| **Session Lifecycle** | Create / reattach / destroy per-thread Docker containers. Containers survive server restarts. |
| **Project Workspace** | Phase-organised directory tree with dependency DAG, lineage tracking, and metadata. |
| **File Explorer** | Navigate workspace directories via `GET /projects/{id}/files`. |
| **Conversation CRUD** | Full create/read/update/delete for conversations and messages. |
| **File Download** | Raw file download + markdown-to-PDF conversion with proper Content-Disposition. |
| **Thread Pool Tuning** | Configurable AnyIO thread pool (default 100 tokens) for I/O-heavy Docker exec workloads. |

### Frontend

| Component | Description |
|---|---|
| **ChatMessage** | Renders user/assistant messages with agent name badges, trace URLs, and file attachments. |
| **ChatInput** | Composer with @mention dropdown, file upload chips, and multi-line input. |
| **FileChips** | Inline file attachment chips in the chat composer — shows upload progress (pending/ready/error) with remove. |
| **MentionDropdown** | Keyboard-navigable @mention dropdown for agent selection in the composer. |
| **ChatSidebar** | Conversation list with create/delete, localStorage persistence, and active conversation tracking. |
| **ArtifactCanvas** | Sandboxed iframe for previewing artifacts (markdown, HTML, Mermaid, binary previews). |
| **FileExplorer** | Navigate the project workspace directory tree. |
| **InspectorPanel** | Side panel showing artifact list with status (ready/pending) per phase. |
| **AgentSidebar / AgentsPanel** | List of available subagents with descriptions and phase numbers. |
| **DiffPreview** | Side-by-side diff view for HITL approval workflow. |
| **ThinkingTab** | Displays model-native reasoning content (extended thinking / reasoning blocks). |
| **TodoList** | Renders `write_todos` tool calls as a structured task list. |
| **ToolCallBlock** | Collapsible tool call display with args and results. |
| **ThemeToggle** | Dark/light mode with CSS variable overrides and localStorage persistence. |
| **SettingsPanel** | Model settings: base URL, API key, agent/vision model. Stored overrides cascade over env vars. |
| **MermaidHighlight** | Self-contained Mermaid syntax highlighter — deterministic regex tokenizer, no Prism dependency. |
| **SkillsPanel / SkillCanvas** | Browse and edit every `SKILL.md` / `LEARNED.md` without leaving the UI. |
| **AgentActivity / SimpleActivityFeed** | Live per-agent activity feed during a streamed run. |
| **FileDropdown / SlashDropdown** | Workspace-file picker and slash-command menu in the composer. |
| **SubagentCard** | Agent info card with icon, description, and phase. |
| **Markdown** | Renders markdown content with syntax highlighting. |
| **AgentMention** | Highlights @mentions in chat messages. |
| **TypingIndicator** | Animated typing dots during agent response. |
| **useSSE** | Hook for Server-Sent Events streaming with auto-reconnect. |
| **useHealthCheck** | Hook for periodic backend health checks. |

### Infrastructure

| Service | Description |
|---|---|
| **Postgres 16** | Conversations + messages persistence. |
| **FastAPI Backend** | Python backend with 30+ REST endpoints + SSE streaming. |
| **Next.js Frontend** | React SPA with TypeScript, Tailwind CSS, and resizable panels. |
| **Docker Compose** | Single-command stack startup with health checks, resource limits, and persistent volumes. |

---

## Agent Roster

| @Mention | Phase | Produces | Engine |
|---|---|---|---|
| **Orchestrator** | — | Dispatches the 7 sub-agents, resolves the dependency DAG | LangGraph + Deep Agents |
| @Ingestion | 1 | `REQUIREMENTS.md`, `GLOSSARY.md`, `CONSTRAINTS.md` | — |
| @Requirements | 2 | `USER_STORIES.md`, `ACCEPTANCE_CRITERIA.md` | — |
| @Architecture | 3 | `ARCHITECTURE.md`, `DATA_MODEL.md`, `ADR.md` | — |
| @API | 3 | `API_SPEC.md` + validated `openapi.yaml` | OpenAPI parser |
| @Planning | 4 | `BACKLOG.md`, `TEST_PLAN.md` | Gherkin parser |
| @DevOps | 4 | `CI_CD.md` + validated `ci/pipeline.yml` | CI pipeline parser |
| @Diagram | 5 | One validated `.mmd` Mermaid model per invocation | Mermaid parser |

### Diagrams

The @Diagram agent is called **once per diagram** by the orchestrator. It produces exactly one Mermaid `.mmd` file per invocation. Standard pipeline (5 diagrams):

| Order | Diagram | Input | Output |
|---|---|---|---|
| 1 | Sequence | `design/API_SPEC.md` + `design/ARCHITECTURE.md` | `diagrams/sequence.mmd` |
| 2 | Class | `design/DATA_MODEL.md` | `diagrams/class.mmd` |
| 3 | State machine | `requirements/USER_STORIES.md` | `diagrams/state.mmd` |
| 4 | ERD | `design/DATA_MODEL.md` | `diagrams/erd.mmd` |
| 5 | Deployment | `planning/CI_CD.md` + `design/ARCHITECTURE.md` | `diagrams/deployment.mmd` |

Other Mermaid types (activity, C4 context, flow) are produced when explicitly requested.

Each `.mmd` file goes through a validation loop via the Mermaid tools (zero syntax errors required) before the agent reports it done. After completion the agent appends fix patterns to the corresponding `LEARNED.md` for self-improvement.

---

## Skills & Self-Improvement

The project ships with **17 skills** under `backend/src/sdlc/skills/`:

| Skill | Type |
|---|---|
| activity-diagram, sequence-diagram, state-machine-diagram | Behavioural diagrams |
| class-diagram, erd, c4-context, deployment-diagram | Structural diagrams |
| api-design, architecture-docs, adr | Design authoring |
| requirements-spec, implementation-plan | Phase authoring (@Requirements, @Planning) |
| ci-cd, secrets-management, test-strategy | Delivery |
| mermaid-v2-reference, general | Cross-cutting |

Each skill is a `SKILL.md` with instructions, a worked example and the failure
modes the artifact schema cannot state. The diagram skills also carry a
`LEARNED.md`: the @Diagram agent's **Phase C** self-improvement loop appends fix
patterns after every generation, so that half of the system improves itself
without manual intervention. The other agents read their skill file by path
(e.g. `/skills/adr/SKILL.md`), named in their prompt template.

Four skills are adapted from public MIT-licensed collections —
`requirements-spec`, `adr` and `implementation-plan` from
[github/awesome-copilot](https://github.com/github/awesome-copilot),
`secrets-management` from [wshobson/agents](https://github.com/wshobson/agents).
Rewritten for this pipeline's artifacts; see `skills/ATTRIBUTION.md`.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop (running)

### Infrastructure

```bash
# Starts postgres + backend + frontend
docker compose up -d

# View logs
docker compose logs -f backend

# Stop (data persists) or wipe
docker compose down            # keep data
docker compose down -v         # wipe everything
```

Connection defaults for postgres are `postgres:password` — the `harness` database is auto-created on first run via `backend/database/init/01-harness.sql`. Override via `DATABASE_URL` in `backend/.env`.

The compose file bind-mounts `backend/src/sdlc/skills/` over the wheel's installed copy at `/usr/local/lib/python3.12/site-packages/sdlc/skills`. Two reasons:
1. The @Diagram agent's Phase C appends fix patterns to `LEARNED.md`; the wheel-installed copy is root-owned and unwritable by the `sdlc` user (uid 1001).
2. Tightened skill files and accumulated `LEARNED.md` history persist on the host filesystem (under git) instead of being wiped by `docker compose up --build`.

Access the UI at **http://localhost:3000**.

### Backend (manual dev)

If you need hot-reload during backend development, run it outside Docker:

```bash
cd backend
cp .env.example .env   # Edit with your API keys
pip install -e .
python main.py          # Dev mode (single-process, auto-reload on changes)
python main.py --prod   # Production mode (gunicorn + 4 uvicorn workers)
```

### Frontend (manual dev)

For frontend development with hot module replacement:

```bash
cd frontend
npm install
npm run dev             # Next.js dev server on port 3000
```

### LangSmith Tracing

To enable observability via [LangSmith](https://smith.langchain.com):

1. Create a LangSmith account and get an API key
2. Set these in `.env`:

```bash
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=sdlc-harness
```

Every orchestrator invocation, sub-agent call, workspace operation, and LLM request is traced.

---

## Configuration

Key environment variables (see `backend/src/sdlc/core/config.py` for the full list):

| Variable | Default | Description |
|---|---|---|
| `AGENT_MODEL` | `mistralai/Mistral-Large-3.1-128B` | LLM model for the orchestrator |
| `AGENT_IDENTITY` | `DevForge` | Name the orchestrator introduces itself with |
| `VISION_MODEL` | `AGENT_MODEL` | Multimodal model for image / screenshot review |
| `VISION_BASE_URL` | `OPENAI_BASE_URL` | Vision model endpoint (separate from text if needed) |
| `VISION_TEMPERATURE` | `0.2` | Low temperature for consistent visual review |
| `OPENAI_API_KEY` | — | API key for the LLM gateway |
| `OPENAI_BASE_URL` | `https://hub.nhr.fau.de/api/llmgw/v1` | LLM gateway endpoint |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@localhost:5432/harness` | Postgres connection |
| `DOCKER_IMAGE` | `python:3.12-slim` | Base image for sandbox containers |
| `DOCKER_POOL_SIZE` | `25` | Docker SDK connection pool size |
| `THREAD_POOL_SIZE` | `100` | AnyIO thread pool tokens |
| `ARTIFACT_CACHE_TTL` | `1.0` | Artifact list cache TTL (seconds) |
| `SDLC_MAX_LLM_INVOCATIONS` | `0` (unbounded) | Cap on model calls per orchestrator run — used by the cost evaluation |
| `SDLC_MAX_INPUT_TOKENS` | `0` (no profile) | Model context window; set it to make summarization triggers accurate |

---

## Evaluation Framework

The harness is evaluated on **what it consumes and how the work is shaped**, not
on the quality of the model it produces. There are exactly two graders:

| Grader | Measures |
|---|---|
| `cost-tokens` | Cost and token consumption (input / output / cached tokens, $ proxy) |
| `process-metrics` | Reasoning tokens, number of LLM invocations, subagent dispatches, elapsed time |

The dataset is a single folder, `evaluation/dataset/`, holding 30 tasks — each a
`task.md` message, a `source/` folder of uploaded documents, and a
`graders.yaml`. Reports are written to `evaluation/results/`.

```bash
cd evaluation && uv sync    # one-time: installs harness-eval + editable backend

uv run python -m harness_eval.tasks run --task Task-23 --trials 3   # one task
uv run python -m harness_eval.tasks run                             # every task
uv run python -m harness_eval list-evaluators
```

See [`evaluation/EVALUATORS.md`](evaluation/EVALUATORS.md) for what each grader
reports, how to read the cost figure, and the task catalogue.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/tracing` | LangSmith tracing status |
| POST | `/projects` | Create project workspace |
| GET | `/projects/{id}/artifacts` | List artifacts with status |
| GET | `/projects/{id}/artifacts/{name}` | Get artifact content (text + binary preview) |
| GET | `/projects/{id}/files` | List workspace directory |
| GET | `/projects/{id}/download` | Download file (raw or markdown→PDF) |
| POST | `/chat` | Send message (non-streaming) |
| POST | `/chat/stream` | Send message (SSE streaming) |
| GET | `/chat/resume` | Resume SSE stream for active run |
| GET | `/history/{thread_id}` | Get message history |
| DELETE | `/session/{thread_id}` | Delete session + container |
| POST | `/upload/{project_id}` | Upload files |
| GET | `/upload/{project_id}` | List uploaded files |
| GET | `/conversations` | List conversations |
| POST | `/conversations` | Create conversation |
| DELETE | `/conversations/{id}` | Delete conversation |
| GET | `/conversations/{id}/messages` | List messages |
| PUT | `/conversations/{id}/messages` | Update message |
| GET | `/conversations/{id}/export` | Export conversation |
| POST | `/conversations/{id}/compact` | Compact conversation history |
| GET | `/agents/custom` | List custom subagents |
| POST | `/agents/custom` | Create custom subagent |
| PUT | `/agents/custom/{id}` | Update custom subagent |
| DELETE | `/agents/custom/{id}` | Delete custom subagent |
| GET | `/tools/registry` | Tool keys custom subagents can request |
| GET | `/settings/model` | Get effective model settings (API key masked) |
| PUT | `/settings/model` | Update model settings (base URL, API key, models) |
| GET | `/skills` | List skills |
| GET | `/skills/{name}` | Skill contents |
| PUT | `/skills/{name}` | Edit a skill file |
| POST | `/chat/abort` | Abort the active run |

---

## Development

### Project Structure

```
backend/
├── main.py                    # Server entry point
├── Dockerfile                 # Backend image
├── src/sdlc/
│   ├── api/app.py             # FastAPI application (30+ endpoints)
│   ├── core/config.py         # Environment-based configuration
│   ├── core/tracing.py        # LangSmith tracing helpers
│   ├── db/                    # SQLAlchemy async engine + Alembic migrations
│   ├── models/schemas.py      # Pydantic request/response models
│   ├── sandbox/docker_backend.py  # Docker sandbox abstraction
│   ├── services/
│   │   ├── agent.py           # LangGraph orchestrator factory
│   │   ├── subagents.py       # 7 subagent definitions + tool wiring
│   │   ├── workspace.py       # Project workspace + phase directories
│   │   ├── artifacts.py       # Artifact schemas + index regeneration
│   │   ├── conversations.py   # Postgres conversation CRUD
│   │   ├── custom_agents.py   # User-created subagent storage
│   │   ├── hitl.py            # HITL approval + ShellGuard
│   │   ├── file_upload.py     # File upload to Docker container
│   │   ├── document_preview.py # Binary → HTML preview conversion
│   │   ├── model_settings.py  # Runtime-tunable model settings (JSON store)
│   │   └── prompts/           # Jinja2 agent prompt templates
│   ├── skills/                # 17 skills (SKILL.md; diagram skills also LEARNED.md)
│   └── tools/                 # Domain tools (Mermaid, OpenAPI, Gherkin, CI, WebSearch, AskUser)
frontend/
├── src/
│   ├── app/                   # Next.js pages + layout
│   ├── components/            # 22 React components
│   ├── hooks/                 # useSSE, useHealthCheck
│   └── lib/                   # API client, types, agent definitions
```

### Commands

| Command | Purpose |
|---|---|
| `python backend/main.py` | Dev server (single-process uvicorn) |
| `python backend/main.py --reload` | Dev server with auto-reload |
| `python backend/main.py --prod` | Production (gunicorn + uvicorn workers) |
| `cd frontend && npm run dev` | Frontend dev server |
| `cd frontend && npm run build` | Frontend production build |
| `cd frontend && npx tsc --noEmit` | TypeScript type-check |
| `cd frontend && npm run lint` | ESLint |
| `cd backend && uv run pytest` | Run backend tests |
| `cd evaluation && uv run python -m harness_eval run --dataset <name>` | Run evaluation pipeline |
| `cd evaluation && uv run python -m harness_eval list-evaluators` | List available evaluators |
| `cd evaluation && uv run python -m harness_eval build-datasets` | Build LangSmith datasets |
| `cd backend && uv sync` | Install backend dependencies |
| `docker compose up` | Start full stack (Postgres, Backend, Frontend) |

### Code Conventions

- **Async throughout**: All I/O-bound operations use `asyncio` — FastAPI endpoints, Docker SDK calls, SSE streaming, SQLAlchemy async sessions, aiosqlite checkpointer.
- **`from __future__ import annotations`**: Used in every Python file for deferred evaluation of type hints.
- **Pydantic v2**: All API schemas use `BaseModel`.
- **Jinja2 templates**: Agent prompts live in `backend/src/sdlc/services/prompts/*.j2`, rendered with schema variables.
- **Deep Agents framework**: Agents are created via `create_deep_agent()` with `CompositeBackend` (FilesystemBackend + StoreBackend) and `HumanInTheLoopMiddleware` for write/edit approval.
- **SSE streaming**: Chat responses stream via `sse-starlette` with a multi-subscriber `RunContext` pattern for resume support.
- **Postgres + SQLite**: Postgres for conversations/messages (SQLAlchemy async + asyncpg + Alembic); SQLite for LangGraph checkpoint persistence (aiosqlite).
- **Frontend**: React SPA via Next.js + TypeScript. 22 components, resizable panels, dark/light theme.
- **Model Settings Cascade**: Runtime-tunable LLM config (base URL, API key, agent/vision model) resolved as stored-override > env-var > built-in default. API key masked at the API boundary.

### Gotchas

- **Docker container lifecycle**: Containers are created per-chat-session and kept on disk across server restarts. They are only removed when a chat is explicitly deleted via `DELETE /session/{thread_id}`.
- **Thread pool sizing**: The AnyIO default thread pool (40 tokens) is too low for concurrent Docker exec calls. `config.py` bumps it to 100 via `THREAD_POOL_SIZE`.
- **Custom agents**: User-created subagents are stored in `backend/data/custom_agents.json` and merged into the orchestrator roster at `create_orchestrator()` time. They take effect on the next chat, not the active one. Reserved names (`ingestion`, `requirements`, `architecture`, `api`, `planning`, `devops`, `diagram`) cannot be overridden.
- **Skills bind-mount**: The Docker Compose file bind-mounts `backend/src/sdlc/skills/` over the wheel's installed copy so that `LEARNED.md` appends persist across image rebuilds.
- **Model settings take effect on new sessions**: Changes made via the Settings panel apply to the *next* chat session, not the active one. Each session builds its model at creation time via `agent._build_model()`.
- **Vision model defaults to agent model**: `VISION_MODEL` defaults to `AGENT_MODEL` and `VISION_BASE_URL` defaults to `OPENAI_BASE_URL`. Override only if the multimodal model is served under a different route than the text model.
