"""Process-metrics evaluator for the SDLC harness.

Measures *how* a pipeline run produced its output — the multi-agent workflow
signals that the quality scorers don't see:

* **Internal reasoning / thinking** — ``reasoning_tokens`` captured from every
  model call (o-series / Claude "thinking" budget). Reported in ``extra``;
  not every provider reports it, so it is informational, not required.
* **Process** — the condensed ``process`` block from ``run_pipeline()``:
  subagent call counts, distinct agents involved, LLM invocations, elapsed_s.
* **LLM invocation count** — ``invocations`` (strict count of every model
  call, including providers that report no token usage).

Like ``cost-tokens`` this is a *measurement* evaluator: the raw values live in
``extra`` and the 0–1 ``score`` is a health gate so the trial still
participates in task-suite ``mean_scores`` aggregation. By default any finite
run scores 1.0; set ``max_llm_invocations`` / ``max_subagents`` /
``max_elapsed_s`` in the example inputs to make the score penalise a
runaway process (e.g. an orchestrator stuck in a tool loop).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Defaults used when a trial reports nothing (flag the gap rather than crash).
DEFAULT_MAX_LLM_INVOCATIONS = 200
DEFAULT_MAX_SUBAGENTS = 30
DEFAULT_MAX_ELAPSED_S = 1800.0


def _get_outputs(run_or_example) -> dict:
    """Safely extract ``outputs`` from a run/example object or a plain dict."""
    if run_or_example is None:
        return {}
    if hasattr(run_or_example, "outputs"):
        return run_or_example.outputs or {}
    if isinstance(run_or_example, dict):
        return run_or_example.get("outputs", {}) or {}
    return {}


def _get_inputs(run_or_example) -> dict:
    """Safely extract ``inputs`` from a run/example object or a plain dict."""
    if run_or_example is None:
        return {}
    if hasattr(run_or_example, "inputs"):
        return run_or_example.inputs or {}
    if isinstance(run_or_example, dict):
        return run_or_example.get("inputs", {}) or {}
    return {}


def process_metrics_evaluator(run, example) -> dict:
    """Score a trial against process health budgets and report its workflow.

    Compatible with both the filesystem task harness (``harness_eval.tasks``)
    and LangSmith ``evaluate()``.
    """
    run_outputs = _get_outputs(run)
    example_inputs = _get_inputs(example)

    usage: dict[str, Any] = run_outputs.get("usage") or {}
    process: dict[str, Any] = run_outputs.get("process") or {}

    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or 0)
    reasoning_tokens = int(usage.get("reasoning_tokens") or 0)
    calls = int(usage.get("calls") or 0)
    invocations = int(usage.get("invocations") or calls or 0)
    model = usage.get("model")

    subagent_calls: dict[str, int] = process.get("subagent_calls") or {}
    agents_involved = process.get("agents_involved") or sorted(subagent_calls.keys())
    subagent_total = sum(subagent_calls.values())
    elapsed_s = process.get("elapsed_s") or run_outputs.get("elapsed_s") or 0.0

    max_invocations = int(
        example_inputs.get("max_llm_invocations") or DEFAULT_MAX_LLM_INVOCATIONS
    )
    max_subagents = int(example_inputs.get("max_subagents") or DEFAULT_MAX_SUBAGENTS)
    max_elapsed = float(example_inputs.get("max_elapsed_s") or DEFAULT_MAX_ELAPSED_S)

    process_ok = (
        invocations <= max_invocations
        and subagent_total <= max_subagents
        and elapsed_s <= max_elapsed
    )
    score = 1.0 if process_ok else 0.0

    parts = [
        f"llm_invocations={invocations}",
        f"subagents={subagent_total} ({len(agents_involved)} kinds)",
        f"reasoning_tokens={reasoning_tokens}",
        f"elapsed={elapsed_s:.1f}s",
    ]
    if model:
        parts.append(f"model={model}")
    if not process_ok:
        parts.append("PROCESS OVER BUDGET")

    return {
        "score": round(score, 4),
        "comment": "; ".join(parts),
        "extra": {
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "reasoning_tokens": reasoning_tokens,
                "calls": calls,
                "invocations": invocations,
                "model": model,
            },
            "process": {
                "subagent_calls": subagent_calls,
                "agents_involved": agents_involved,
                "llm_invocations": invocations,
                "elapsed_s": elapsed_s,
            },
            "budget": {
                "max_llm_invocations": max_invocations,
                "max_subagents": max_subagents,
                "max_elapsed_s": max_elapsed,
            },
        },
    }