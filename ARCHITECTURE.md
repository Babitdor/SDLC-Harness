# SDLC Harness — Internals

**How the harness works.** A multi-agent system that turns a rough product brief
into a traceable specification set — and the machinery underneath that keeps
every claim it makes checkable.

> Describes the system as built. Behaviour marked as a constraint is current,
> not permanent.

---

## Contents

**Runtime**

1. [Service topology](#1-service-topology)
2. [Request lifecycle](#2-request-lifecycle)
3. [Orchestrator and subagents](#3-orchestrator-and-subagents)
4. [The sandbox](#4-the-sandbox)

**State**

1. [Workspace and bookkeeping](#5-workspace-and-bookkeeping)
2. [Skills and the learning loop](#6-skills-and-the-learning-loop)
3. [What persists, and where](#7-what-persists-and-where)

**Interface**

1. [Streaming protocol](#8-streaming-protocol)
2. [Frontend state](#9-frontend-state)
3. [Model configuration](#10-model-configuration)

**Measurement**

 1. [Evaluation harness](#11-evaluation-harness)
 2. [Known constraints](#known-constraints)

---

## 0. What it is

You upload requirements documents. An orchestrator reads them, plans a route
through the RFLP pipeline — *Requirements, Functional, Logical, Physical* — and
delegates each phase to a specialist subagent. Those subagents write real files
into a real filesystem, validate them with real parsers, and record what they did.

The design commitment that shapes everything else: **agents do not exchange
model content in messages. They exchange files.** A subagent receives one
instruction string and finds everything else on a shared disk. That makes each
phase's output inspectable, diffable, and re-runnable, and it means a lost
message costs a narration rather than a model.

| | |
| --- | --- |
| **Stack** | FastAPI · deepagents 0.7 · LangGraph 1.2 · Next.js 16 · Postgres · Docker |
| **Agents** | 1 orchestrator, 9 phase subagents, 13 domain tools |
| **Artifacts** | 11 declared deliverables per project, in 4 phase directories |
| **Isolation** | One disposable Linux container per chat thread |

---

## 1. Service topology

Three containers under one Compose project. Only two hold application code;
the third is the database the agents' transcripts live in.

| Service | Role | Notes |
| --- | --- | --- |
| `backend` | FastAPI app, agent runtime, SSE | Single gunicorn worker — run state is in-process and cannot cross a fork |
| `frontend` | Next.js chat client | Baked into its image; source edits need a rebuild |
| `postgres` | Conversations and messages | The durable transcript |

> ⚠️ **The single worker is load-bearing.** Detached run tasks, SSE subscriber
> queues, pending approval futures and the session cache all live in process
> memory. With more than one worker, a stream sticks to one process while a
> follow-up request round-robins to another that has no record of the run.

---

## 2. Request lifecycle

What happens between pressing Send and the first token appearing. The ordering
matters: the run is detached from the HTTP response, so closing the tab does not
stop the agent.

1. **Session resolve** — `POST /chat/stream` looks up the thread in the
   in-process session cache, or builds an orchestrator and attaches a Docker
   sandbox by deterministic container name.
2. **Workspace ensure** — creates the phase directories if absent, then
   re-points `/workspace/current` at this request's project so every prompt's
   fixed path resolves correctly.
3. **Inventory snapshot** — records every file and mtime *before* the agent
   runs, so the post-run diff can classify each change as produce, update,
   remove or upload.
4. **Detached runner** — spawns an `asyncio` task holding a RunContext (an event
   history plus a set of subscriber queues). The task outlives the HTTP response.
5. **Stream and fan-out** — the agent graph streams in `messages` and `events`
   modes with subgraphs enabled. Each chunk becomes a typed SSE event appended
   to history and pushed to every subscriber.
6. **Persist and reconcile** — on exit the assistant turn is written to Postgres
   with its tool calls and reasoning, the workspace is re-scanned, and the change
   log, lineage and index are regenerated.

Because the runner is detached, `GET /chat/resume` can re-attach at any point. A
resumer receives the run's entire event history replayed, then tails live events
from its own queue.

---

## 3. Orchestrator and subagents

The orchestrator plans and delegates; it does not author model content. Seven
subagents each own one phase and one set of deliverables.

```
@Ingestion      →  REQUIREMENTS · GLOSSARY · CONSTRAINTS
      ↓
@Requirements   →  USER_STORIES · ACCEPTANCE_CRITERIA
      ↓
@Architecture   →  ARCHITECTURE · DATA_MODEL · ADR
      ↓
@API            →  API_SPEC · openapi.yaml (validated)
      ↓
@Planning       →  BACKLOG · TEST_PLAN
      ↓
@DevOps         →  CI_CD · ci/pipeline.yml (validated)
      ↓
@Diagram        →  5 × .mmd (validated Mermaid)
```

`@Architecture` and `@API` share phase 3; `@Planning` and `@DevOps` share phase
4. The pipeline stops at specs — nothing in the roster produces application
code.

### What a subagent actually receives

This is the part most people get wrong when reasoning about the system.
Delegation replaces the subagent's entire message history with **one human
message containing the orchestrator's instruction string**. No conversation
history, no user request, no file contents.

The grounding channel is the shared filesystem. Every subagent inherits the same
composite backend, so it reads the same `/workspace/current` the orchestrator
sees. This is why the file-based handoff matters: a detail dropped from the
instruction string is recoverable from disk, while a detail that only ever
existed in a message is not.

### MCP tools

External MCP servers are configured from the sidebar's MCP tab and stored in
`backend/data/mcp_settings.json` (gitignored; same shape of store as model
settings, with credential values write-only — the API returns key names only).

Three constraints shape the wiring:

- **The load is async, the consumer is not.** `create_orchestrator()` and
  `_build_tools()` are synchronous, so `services/mcp.py` loads tools into a
  module cache (`refresh()`) from the lifespan and from every settings
  endpoint; `_build_tools()` then only reads it. A cold cache means "no MCP
  tools", never an error.
- **Tools are baked into the subagent spec**, so each MCP mutation calls
  `_invalidate_all_orchestrators()` — otherwise a running thread keeps the
  tool set it was created with.
- **Failure degrades per server.** One unreachable server contributes nothing
  and records its error for the panel; the remaining servers and all built-in
  validators still load. Validators stay authoritative — MCP tools add
  context, they never replace a check.

**The catalog is presets, not hardcoded wiring.** `mcp_settings.PRESETS` lists the
phase-mapped servers (name, transport, remote URL or command, assigned agents, and
what each one unlocks). Boot seeds it exactly once — the store records
`presets_seeded` so a restart never resurrects a server the user deleted;
`POST /mcp/servers/presets` restores only the missing entries and never
overwrites an edited one. Zero-auth servers (fetch, context7) ship enabled;
everything requiring a token ships disabled with an `AUTH` marker in the panel,
because seeding an unauthenticated server just paints a failed row.

Python stdio servers run as `uvx <package>` subprocesses, which is why `uv` is
installed in the runtime image and not only the builder.

The client is `langchain-mcp-adapters`, deprecated upstream in favour of
`langchain.mcp`, which the pinned langchain does not yet ship (verified by
import against 1.3.18 and the latest extra). The import is guarded: without
the package the tab reports the missing adapter instead of failing.

### Middleware stack

| Layer | Purpose |
| --- | --- |
| `ShellGuard` | Deterministic block on destructive shell commands — not a model judgement |
| `ModelRetry` | 3 retries, exponential backoff, for transient provider failures |
| `ModelCallLimit` | Opt-in invocation ceiling via `SDLC_MAX_LLM_INVOCATIONS`; off by default |
| `SubAgent` | Supplies the `task` tool and compiles each subagent graph |
| `Summarization` | Compacts context at a threshold; offloads evicted turns to a file |

Every phase prompt carries an explicit anti-fabrication policy: verify upstream
artifacts exist and contain real content, and stop rather than invent. An
under-specified subagent is designed to halt, not guess.

### Prompt caching and token accounting

96% of this pipeline's tokens are **input** tokens. One measured trial:
199 model calls, 6,224,330 input / 364,631 output, p95 63k input per call,
**`cached_tokens` = 0**. Every one of those calls re-sends the same prefix —
the orchestrator system prompt (~3.9k tokens once deepagents appends its tool
and filesystem hints) plus the tool schemas. On a 20-turn chat that prefix is
the majority of what is billed.

Caching that prefix is the provider's job; nothing here can serve it locally.
What this codebase owns is the *precondition* and the *measurement*:

| Concern | Where |
| --- | --- |
| Prefix byte-stability (system prompt, tool schemas, earlier messages) | `services/agent.py`, guarded by `tests/test_prompt_cache.py` |
| Cache routing hint | `_prompt_cache_key()` — `PROMPT_CACHE_KEY=auto\|on\|off` |
| What the provider actually reported | `services/usage.py`, `UsageLedger` |
| Visibility | `GET /conversations/{id}/usage` + one `Run usage` log line per run |

**Stability is the contract.** A provider prefix-caches on exact bytes, so one
timestamp in the system prompt, one reordered tool schema, or one rewritten
history message turns every later call into a miss — silently, with no error,
visible only as the token bill. `tests/test_prompt_cache.py` builds the
orchestrator twice with a recording model and fails if the system prompt, the
tool schemas, or the shared message prefix differ between turns or between
builds. It was mutation-checked: injecting a timestamp into the system prompt
fails it.

**The hint is deliberately conservative.** `prompt_cache_key` is documented for
OpenAI's own endpoint; an unknown OpenAI-compatible gateway may reject an
undocumented body field, which would fail every chat rather than slowly. So
`auto` (the default) sends it to `api.openai.com` only. Use `on` for a gateway
(LiteLLM forwarders) known to accept it, `off` to never send it. Providers that
cache without a hint — DeepSeek, Anthropic, vLLM, OpenAI itself — need no
configuration at all; they cache on prefix repetition alone.

**Accounting is attached to the model, not to a graph config.** deepagents
hands one model instance to the orchestrator and to every delegated subagent,
so a single `UsageRecordingHandler` on that instance counts the whole run,
including nested calls, and cannot be missed by a future invoke site. A raising
handler would abort the model call, so it swallows everything (`raise_error =
False`).

Cached tokens are a **subset** of input tokens, never additive. `cache_hit_ratio`
is `cached_tokens / input_tokens` for the thread: 0.0 with a cold cache,
approaching 1.0 as the prefix is served from cache. The ledger is process-local,
like the session cache — a diagnostic, not a billing record.

### Caveman: read less, natively

Caching lowers the price of a repeated prefix. It does nothing for the number
that dominates the bill: *new* tool-result text — a 4k-line validator report, a
`read_file` of a 900-line artifact, a subagent's full report handed back through
`task()`. Those land in the message list at full length, then get resent on every
call that follows.

The idea of shrinking them before the model reads them is Caveman's "read less"
(github.com/JuliusBrussee/caveman, Apache-2.0). Upstream ships it as a Go runtime
the framework adapter talks to over HTTP. `services/caveman.py` is a native port
of the contract, because a sidecar process is a bigger change to this stack than
the problem justifies: docker-compose gains a service, the backend gains a network
dependency, and section 3's middleware list gains a failure mode.

| Concern | Where |
| --- | --- |
| Format routing + compressors | `services/caveman.py` — `json`, `log`, `diff`, `table`, `html`, `text` |
| The hook | `CavemanToolMiddleware.wrap_tool_call` / `awrap_tool_call` |
| Reach | orchestrator middleware list **and** `_retry_middleware()` (all 7 subagents) |
| Recovery | originals in `CAVEMAN_STORE_DIR`, `caveman_retrieve(handle, offset, limit)` |
| Voice | `services/prompts/_caveman.j2`, included by `orchestrator.j2` only |
| Measurement | `CavemanStats`, logged per run as `Caveman read-less totals` |

Three properties are non-negotiable, and each has a test:

1. **Deterministic.** Compression is a pure function of the bytes — no model call,
   no timestamp, content-addressed handles. A rewrite that varied per turn would
   change the prefix and defeat the caching above.
2. **Findings survive.** Validation output is this pipeline's product. Any line
   matching `error|warn|fail|exception|traceback|conflict|invalid|…` is kept
   verbatim in every format, however deep in a log it sits. A compacted report
   that dropped a finding would let an agent claim a clean run it never had.
3. **Reversible.** The exact bytes are stored before the shortened view replaces
   them, and the footer names the handle. If the store write fails, nothing is
   shortened — the upstream rule, kept.

Attaching the hook in two places rather than per call site is deliberate:
`wrap_tool_call` sits where *every* tool result crosses, so a tool added
tomorrow is covered without anyone remembering to opt in, and the orchestrator's
`task()` results (the largest payloads in a run) are covered by the same object
as a subagent's `read_file`.

The voice half is deliberately narrow. Terse prose belongs in chat, where a human
scans for the answer; artifacts are the deliverable and are read by the next
agent, so `_caveman.j2` states the carve-out explicitly and only
`orchestrator.j2` includes it. It is short on purpose — a prompt is billed on
every call, so a rule set that does not pay for itself in a few paragraphs saves
nothing.


---

## 4. The sandbox

Each chat thread owns a `python:3.12-slim` container, named deterministically
from the thread id so a backend restart re-adopts the same one and workspace
state survives. Agent shell commands and file operations execute inside it; the
backend reaches the host Docker socket to create these as siblings, not children.

### Isolation floor

The container is single-tenant and runs shell that is ultimately steered by
untrusted uploaded documents, so creation is hardened by default and the knobs
are config, not code:

| Setting | Default | Why |
| --- | --- | --- |
| `network` | `none` | Nothing in the sandbox needs egress; the model call and every validator run in the backend. A bridge network also put the harness API (published on `0.0.0.0:8000`, unauthenticated) one `curl` away from agent shell. |
| `cap_drop` | `["ALL"]` | `CapEff` is `0000000000000000` inside the container — verified live. |
| `security_opt` | `no-new-privileges` | No setuid path back up. |
| exec user | `1000:1000` | Every agent-facing `docker exec` (shell, file ops, artifact reads) drops to this uid. PID 1 alone is root, long enough to `chmod` the workdir. |
| `mem_limit` / `nano_cpus` / `pids_limit` | `2g` / 2 / 512 | One chat's runaway script must not starve the host or the other chats. |
| `init` | on | tini reaps; `tail -f /dev/null` as PID 1 does not. |
| labels | `harness.sandbox` | Lets startup GC find orphans instead of guessing from names. |

Two consequences worth knowing. `chown` is unavailable (CAP_CHOWN is dropped), so
workdir and upload ownership is fixed with `chmod` — non-recursive for the
workdir, per-file for `put_archive` uploads, because root without CAP_FOWNER may
only chmod what it owns. And every command is wrapped in coreutils `timeout`, so
a hung command returns exit 124 with an explanatory note instead of pinning an
executor thread for the life of the process.

Startup does two daemon round trips off the event loop: `ensure_image` (pull the
sandbox image if absent, so the first chat does not pay for it) and
`gc_orphan_containers` (remove labelled sandboxes that have been stopped for
`DOCKER_ORPHAN_TTL_HOURS`). Neither can fail boot.

Containers created before this floor existed keep their original config: a
running container cannot be re-created without destroying its workspace, and
silently deleting a user's chat state to harden it is not a trade this code
makes. They are unlabelled, so GC never touches them; they pick up the floor
the next time the chat is deleted and recreated.

### Path routing

A composite backend splits the agent's filesystem across four stores by path
prefix. The agent sees one namespace; each prefix lands somewhere with different
durability.

| Prefix | Backed by | Lifetime |
| --- | --- | --- |
| `/memories/` | LangGraph store | Shared across threads |
| `/skills/` | Host bind-mount | Permanent, under version control |
| `/conversation_history/` | Backend volume | Survives sandbox recycling |
| everything else | Sandbox container | Dies with the container |

### Output limits

Shell output is capped at 100 KB. The cap slices *bytes*, not characters — a
distinction that matters when the source documents are German and every umlaut
is two bytes — and appends an in-band notice so the model knows the tail exists:

```
... Output truncated at 100000 bytes. Re-run scoped to
the part you need (head/tail/sed -n/grep) —
do NOT infer the omitted content.
```

The marker is the point. A silently shortened file is indistinguishable from a
complete one, and a model reading a truncated document will confidently complete
the pattern.

---

## 5. Workspace and bookkeeping

One directory per project, organised by engineering phase rather than by file
type — so the layout itself encodes the pipeline.

```
/workspace/current/          ← stable alias, re-pointed each run
├── sources/                 uploaded input documents
├── requirements/            REQUIREMENTS · GLOSSARY · CONSTRAINTS · USER_STORIES · ACCEPTANCE_CRITERIA
├── design/                  ARCHITECTURE · DATA_MODEL · ADR · API_SPEC · openapi.yaml
├── planning/                BACKLOG · TEST_PLAN · CI_CD · ci/pipeline.yml
├── diagrams/                5 validated .mmd Mermaid diagrams
├── metadata/                lineage.json, project_graph.json
├── index.md                 current artifact state
└── log.md                   chronological change history
```

The `current` alias exists because prompts are module-level constants rendered
once at import, while the project id arrives per request. A re-pointable symlink
gives every agent one always-correct path without re-rendering templates or
risking a stale baked-in id.

### The change record

After every run the system diffs the before and after inventories and appends
rows to `log.md` itself. Agents are explicitly forbidden from writing those rows
— they may add a single `note` row for rationale, nothing more.

| Column | Meaning |
| --- | --- |
| `Action` | `produce` · `update` · `remove` · `upload` · `note` |
| `Declared-From` | The project graph's *declared* upstream dependency — and `-` when that file is not present |
| `Target` | The artifact that changed |

> **`Declared-From` is not observed provenance.** A diff of two filesystem
> snapshots cannot see which input a model actually read. The column names a
> declared dependency, and prints `-` when it cannot be verified — because a
> plausible-looking source that was never uploaded is worse than no answer at all.

---

## 6. Skills and the learning loop

Seventeen skill directories under `/skills/`, each a `SKILL.md` — how to author
one artifact type, with a worked example and the failure modes the schema cannot
state. The nine diagram skills also carry a `LEARNED.md` that accumulates fix
patterns discovered in earlier sessions.

The other four are named by path in their owner's prompt template —
`requirements-spec` in `requirements.j2`, `adr` in `architecture.j2`,
`implementation-plan` in `planning.j2`, `secrets-management` in `devops.j2` — read
once at the start of that phase. They carry no `LEARNED.md` because their agents
run no Phase C loop.

The `@Diagram` agent runs a three-phase loop:

- **Phase A** — read `SKILL.md` and both the per-diagram and general
  `LEARNED.md`, once.
- **Phase B** — author the model, validate it with the Mermaid validator, and
  repair errors.
- **Phase C** — append what was learned, anchored on a stable footer line so
  appends never clobber prior sessions.

> ⚠️ **Phase A reads these files in full, every session.** That makes the
> learning loop a direct, compounding context cost — anything written there is
> paid for again on every future run of that diagram type. A no-signal entry is
> not free.

The correct shape of a no-fix entry is exactly two lines. When the template
invited elaboration, the model filled it: one file reached 129 KB, of which 91%
was prose inside `No new fixes (…)` parentheticals — roughly 32,000 tokens
re-read on every session, for zero information.

---

## 7. What persists, and where

Four stores with genuinely different durability. Knowing which is which explains
most surprising behaviour.

| Store | Holds | Survives |
| --- | --- | --- |
| Postgres | Conversations, messages, tool calls, reasoning, attachments | Everything |
| SQLite checkpointer | LangGraph agent state per thread | Backend restarts |
| Backend volume | Compaction archives, evicted history | Backend rebuilds |
| Sandbox container | The entire project workspace | — nothing |

> ❗ **The workspace is the least durable store and holds the most valuable
> output.** Sandboxes mount no volumes; artifacts, `log.md` and `index.md` all
> die with the container. Anything you need to keep should be downloaded or
> exported.

### Message shape

A row carries `role`, `content`, `agent_name`, and three JSONB sidecars —
`tool_calls`, `attachments`, `reasoning`. The whole run's tool calls are attached
to the assistant turn, which is what lets an export or a reload reconstruct what
the agent actually did rather than only what it said.

### Compaction

`POST /conversations/{id}/compact` summarises a thread to reclaim context. It is
deliberately ordered so that everything which can fail happens before anything
destructive: archive the full transcript, summarise, and only then replace the
message table and clear the checkpoint state. If archiving fails, compaction
aborts.

The summary includes tool inputs and results, not just prose. A summary of claims
with the evidence stripped out cannot be checked against anything.

---

## 8. Streaming protocol

Server-sent events, one JSON object per event, discriminated by `type`.

| Event | Carries |
| --- | --- |
| `token` | Visible assistant text, plus the emitting agent |
| `reasoning` | Model thinking, split from the visible answer |
| `tool_call` | Tool name and id — arguments arrive separately |
| `tool_args` | Streamed argument deltas, keyed by tool id |
| `tool_result` | Result text, capped and marked |
| `subagent_started` / `_completed` | Delegation boundaries and the namespace path |
| `todos` | A checklist, orchestrator-level or per subagent |
| `done` / `error` | Terminal. Always sent, even when there was no run to replay |

### Replay and the sequence number

Every event carries a monotonic `_seq` inside its payload. This exists because
*any* new subscriber to a run receives the whole history replayed before live
events begin — so without a sequence, a re-attach is indistinguishable from new
output and the run's text gets painted twice.

The number travels inside the JSON rather than as a top-level SSE field, because
the server framework constructs events by keyword expansion and rejects unknown
keys. The client keeps a per-thread high-water mark and discards anything at or
below it.

> That mark is only valid while the state it describes still exists. Switching
> threads reloads messages from Postgres, at which point the replay becomes the
> only source of an in-flight run's output — so the mark is cleared alongside the
> reload. Discard one, discard the other.

---

## 9. Frontend state

Chat state is keyed per thread — a map from thread id to
`{ messages, subagents, todos }` — and the visible thread is a lookup, not a
separate copy.

This matters more than it sounds. When the three slices were global, a background
run had nowhere of its own to write, so its events landed on whatever thread was
on screen and had to be fenced off by guards at every handler. Those guards were
unsound: they ran when an event *arrived*, not when its batched update *flushed*,
so anything queued moments before a thread switch sailed straight past them.

With per-thread state the guards are unnecessary and have been removed. Streaming
updates are batched per frame and keyed by thread, so a flush that lands after a
switch updates its own run's slot. Switching threads is a map read with no
blanking or refetch.

> ⚠️ **One live stream at a time.** A single abort controller means switching
> threads tears down the SSE you were watching. The backend run continues and
> replays on return — but a background thread does not paint while you are
> elsewhere. Per-thread controllers are the remaining step.

---

## 10. Model configuration

Any OpenAI-compatible endpoint. Settings resolve through a strict precedence, and
the top layer surprises people:

```
stored JSON overrides  (Settings UI)   ← always wins
        ↓
compose environment   (docker-compose.yml)
        ↓
.env file             (backend/.env)
        ↓
built-in defaults
```

> ❗ **Editing `.env` changes nothing while a stored override exists.** The
> Settings UI writes to a JSON store on the backend volume that outranks every
> file and survives rebuilds. Clearing a field in the UI is what makes `.env`
> authoritative again.

Changing model settings invalidates every cached orchestrator, so existing
threads pick up the change on their next message — not only new ones. Rebuilding
is cheap: the new backend re-adopts the same container by name and the workspace
is untouched.

### Context window

`SDLC_MAX_INPUT_TOKENS` declares the endpoint's real input limit, which sets the
summarization trigger. Unset means *unknown*, and falls back to a conservative
fixed threshold.

This is configuration rather than a constant for a reason. Under-declaring makes
the agent compact at a fraction of its capacity, discarding context into a lossy
summary; over-declaring is worse, putting the trigger above the provider's real
limit so summarization never fires and the request hard-errors on overflow
instead.

---

## 11. Evaluation harness

A standalone runner executes task suites against the live pipeline and scores the
output with 26 graders. A task is a directory: a prompt, optional `source/`
inputs, declared grader bindings, and optional ground-truth files.

| Grader family | Measures |
| --- | --- |
| Phase quality | Requirements, use cases, activities, function tree, principle solutions — INCOSE conformance and LLM judgement |
| Artifact integrity | Mermaid / OpenAPI / Gherkin / CI-pipeline parse validity, defect density, cross-model consistency |
| Traceability | Requirement → artifact chains, allocation, verification linkage |
| Completeness | Whether the deliverables the brief names actually exist |
| Measurement | Tokens, cached tokens, cost, LLM invocations, subagent dispatches |

### Scoring budgets

The cost grader scores a headroom ratio — `min(cap/cost, cap/tokens)` — so a
score falls as overage grows. The inverted form is a genuine trap: `cost/cap`
rises with overage and then clamps, which awards the most expensive run a perfect
score.

> ❗ **A cost eval without a correctness grader is gameable.** Any change that
> makes the agent give up early scores *better* on both cost and process while
> shipping nothing. Completeness must be wired alongside, or the measurement
> rewards failure.

Prices are resolved per model from a rate table. When a model is absent from it,
the estimate falls back to a placeholder and flags itself — a fallback-priced run
ranks runs against each other but its absolute dollars are not spend.

---

## Known constraints

Current limits worth knowing before you rely on something.

- **Workspace durability.** Sandboxes mount no volumes. Project artifacts do not
  survive container removal.
- **One visible stream.** Background runs continue but do not render until you
  return to them.
- **Single backend worker.** Horizontal scaling needs run state moved out of
  process memory.
- **Specs, not software.** No agent produces application code; the deepest
  artifact is a validated contract (OpenAPI, CI pipeline, Mermaid model).
- **Declared, not observed, provenance.** The change log records intent from the
  project graph, verified only for existence. Real derivation lives in the
  artifacts.
