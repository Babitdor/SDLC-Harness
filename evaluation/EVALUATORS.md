# SDLC Harness Evaluation

The harness is evaluated on **what it consumes and how the work is shaped** —
never on the quality of the model it produces. Two graders exist, and only two:

| Grader | Measures |
|---|---|
| `cost-tokens` | Cost and token consumption |
| `process-metrics` | Internal reasoning / thinking, process shape, number of LLM invocations |

Artefact-quality graders (diagram validity, requirements quality, traceability,
layout, LLM judges, ground-truth fidelity) were removed. `tests/test_pipeline.py::
test_registry_is_measurement_only` fails if any grader other than these two is
registered, so widening the scope has to be a deliberate change.

## Task corpus

- `Task-S1` … `Task-S3` — SDLC briefs (event ticketing, delivery pipeline,
  library lending API). These are the current corpus: each one exercises the
  `sources → requirements → design → planning → diagrams` pipeline.
- `Task-1` … `Task-30` — the legacy MBSE/SysML corpus, kept for history. The
  converted roster cannot satisfy those briefs (they ask for SysML models), so
  treat their results as a baseline for cost, not for output.

---

## `cost-tokens`

Reads the usage that `run_pipeline()` captures on every model call — including
nested subagent calls — and prices it from the table in `harness_eval/costs.py`.

**Reports** (`extra`): input / output / total / cached tokens, call count, model,
max and p95 input tokens per call, `cost_usd`, the rates used, and
`used_fallback_price`.

**Score:** `1.0` inside budget. Over budget it is the headroom ratio
`min(max_cost / cost, max_tokens / tokens)`, so it falls as the overage grows.
Defaults: `max_cost_usd = 1.00`, `max_total_tokens = 1,500,000`.

**Reading the dollar figure.** It is a proxy: what the workload would cost on the
model vendor's own API at the rate in `costs.py`. It is not an invoice — a run on
a subscription-metered gateway such as Ollama Cloud is not billed per token.
Check `used_fallback_price` before quoting any figure; `true` means the model had
no pinned rate and a default was used. Token counts are measured directly and are
provider-independent; prefer them as the primary reported quantity.

## `process-metrics`

Reports how the run was carried out:

- **Internal reasoning / thinking** — `reasoning_tokens`, read from every model
  call in any of the standard shapes (`completion_tokens_details`,
  `output_tokens_details`, langchain `output_token_details`).
- **LLM invocations** — `invocations`, a strict count of every completed model
  call, including calls whose provider reports no usage.
- **Process** — per-subagent dispatch counts, the distinct agents involved, and
  elapsed wall time.

**Score:** `1.0` within all process budgets, `0.0` if any is exceeded — a
pass/fail gate, so a small overrun scores the same as a large one. Defaults:
`max_llm_invocations = 200`, `max_subagents = 30`, `max_elapsed_s = 1800`.

**Reasoning tokens depend on the provider.** Ollama's OpenAI-compatible endpoint
returns only `prompt_tokens`, `completion_tokens` and `total_tokens`, so
`reasoning_tokens` reads 0 there. Report it as unavailable on such providers,
not as a measured zero.

### Budgets

The task runner does not pass per-task budget values to the graders, so every
task is scored against the defaults above. Those were calibrated on a minimal
task; a full four-phase RFLP build (e.g. Task-24) can exceed them. The measured
values in `extra` are unaffected — only the 0–1 score is.

---

## Dataset

There is one dataset folder: `evaluation/dataset/`. Each task is a directory:

```
evaluation/dataset/Task-N/
  task.md        the user's message to the harness
  source/        the documents uploaded with it
  graders.yaml   project_id, prompt file, and the two graders
```

Every task must ship at least one source document. A task with none halts at
ingestion and measures only orchestration overhead.
`tests/test_task_harness.py::test_dataset_samples_are_measurable` enforces this,
along with unique container-safe project ids and the absence of gold `expected/`
folders.

| Tasks | Scope | Sources |
|---|---|---|
| 1 | Warehouse — full RFLP | requirements + morphological box |
| 2–14 | Single-diagram tasks across 13 domains | 1 requirements document each |
| 15–22 | Full RFLP across 8 domains (UAV, ADAS, infusion pump, grid, railway, naval, manufacturing, satcom) | 4 documents each |
| 23 | 22 kW AC charging point — the *simple* reference case | 1 specification |
| 24 | 700 bar hydrogen refuelling station — the *complex* reference case | 4 documents |
| 25 | Minimal warehouse — the smallest complete model build | 1 requirements document |
| 26–30 | Full RFLP: UAV, greenhouse, AMR, EV charging network, cold chain | requirements + morphological box |

Tasks 23 and 24 are the paired cost walkthrough: the variable between them is
pipeline depth, not domain difficulty.

### Sample standard

Source documents are written as an industrial requirements register would be:

- a document header (ID, revision, status, scope) and a register of the real
  standards or regulations that govern the domain;
- `REQ-NNN` / `REQ-NF-NNN` requirements, one "shall" each, quantified, each with a
  verification method;
- a constraints table with `C`-IDs traced to requirements, and a worked check
  wherever the numbers must close (braking, torque, power, energy budgets);
- an open-points section stating what the sources leave undetermined;
- for morphological boxes, option characteristics and a known-incompatibilities
  list, so a concept can be selected and defended from the sources.

The brief is a realistic message: it points to the attached documents rather than
restating them, and it must not contradict them.

---

## Running

```bash
cd evaluation && uv sync

# one task, three trials (the dataset folder is the default suite)
uv run python -m harness_eval.tasks run --task Task-23 --trials 3

# every task
uv run python -m harness_eval.tasks run

# keep the per-trial sandbox for inspection
uv run python -m harness_eval.tasks run --task Task-24 --keep-containers

# list registered graders
uv run python -m harness_eval list-evaluators
```

Reports are written to `evaluation/results/report-<unix-time>.json`, outside the
dataset folder.

The model and endpoint come from `backend/.env` (`AGENT_MODEL`,
`OPENAI_BASE_URL`), which `config.py` loads with `override=True` — it takes
precedence over shell variables.

### Known runner issues

- The runner writes its report and then does not exit. When queuing runs, detect
  the new report file rather than waiting on the process.
- `artifact_contents` is not persisted into the report and sandboxes are removed
  at the end of a run, so produced artefacts cannot be inspected afterwards
  unless `--keep-containers` is passed.

Standalone measurement without the task suite:

```bash
uv run python -m harness_eval.measure --prompt "..." --trials 3 --output cost_report
```
