"""Cost & token-usage evaluator for the SDLC harness.

Measures how many tokens a pipeline trial consumed and estimates its USD cost.
This is a *measurement* evaluator rather than a quality scorer:

* The raw token split, LLM-call count, model, and estimated cost are returned
  in ``extra`` (they are not standard LangSmith result keys).
* ``score`` is a budget-aware 0–1 value so the trial still participates in the
  task-suite ``mean_scores`` aggregation. The score is ``1.0`` inside budget;
  over budget it is ``min(max_cost/cost, max_tokens/tokens)`` — a headroom
  ratio that falls as the overage grows — so the flag and the score use the
  same dual cap (cost **and** tokens) and always agree in direction.

Budgets are read from ``example.inputs`` so a task's ``task.md`` frontmatter or
the run inputs can tune them (e.g. ``{"max_total_tokens": 100000}``).
"""

from __future__ import annotations

import logging
from typing import Any

from harness_eval.costs import estimate_cost, get_prices

logger = logging.getLogger(__name__)

# Defaults used when a trial reports no usage (flag the gap rather than crash).
#
# Observed Task-1 baseline (20-trial batch, report-1787684947.json):
#   mean cost $1.23, median $1.15, min $0.90, max $2.25
#   mean tokens 1.14M/trial, min 843K, max 1.50M
# The old 200K token cap was ~5x below real consumption, which made the
# ``OVER`` flag fire on tokens for every trial (semantics drift: cost-only
# score disagreed with the token cap). The cap is raised to 1.5M so the flag
# and score share one budget envelope — see R3 in the cost-eval feasibility
# plan.
DEFAULT_MAX_COST_USD = 1.0
DEFAULT_MAX_TOKENS = 1_500_000


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


def cost_tokens_evaluator(run, example) -> dict:
    """Score a trial against a token/cost budget and report its usage.

    Compatible with both the filesystem task harness (``harness_eval.tasks``)
    and LangSmith ``evaluate()``.
    """
    run_outputs = _get_outputs(run)
    example_inputs = _get_inputs(example)

    usage: dict[str, Any] = run_outputs.get("usage") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or 0)
    calls = int(usage.get("calls") or 0)
    model = usage.get("model")
    # Subset of input_tokens served from the prompt cache. 0 means either
    # "caching off" or "provider does not report it" — the two are
    # indistinguishable here, which is itself worth seeing in the report.
    cached_tokens = int(usage.get("cached_tokens") or 0)
    max_in_per_call = int(usage.get("max_input_tokens_per_call") or 0)
    p95_in_per_call = int(usage.get("p95_input_tokens_per_call") or 0)

    prices, used_fallback = get_prices(model)
    est = estimate_cost(
        input_tokens, output_tokens, model,
        prices=prices, used_fallback=used_fallback,
    )

    max_cost = float(example_inputs.get("max_cost_usd") or DEFAULT_MAX_COST_USD)
    max_tokens = int(example_inputs.get("max_total_tokens") or DEFAULT_MAX_TOKENS)

    budget_ok = est["cost_usd"] <= max_cost and total_tokens <= max_tokens
    # Dual-cap score, as a budget *headroom* ratio: cap / actual. In budget
    # the score is 1.0; over budget it falls toward 0 as the overage grows,
    # and the binding (worst-breached) cap sets it.
    #
    # The previous form used actual/cap, which ROSE with overage and then
    # clamped at 1.0 — so a trial at 2.25x the cost cap scored a perfect
    # 1.000, identical to an in-budget run, while a trial 1% over scored
    # 0.64. Measured on the 20-trial CostEvals batch, r(cost, score) was
    # +0.890: the grader was rewarding expensive runs. Both caps are
    # divided into, not by, so more overage is always a lower score.
    if budget_ok:
        score = 1.0
    else:
        # Only breached / non-zero denominators contribute; an unbreached
        # cap yields a ratio > 1 and is clamped away by the min with 1.0.
        ratios = []
        if est["cost_usd"] > 0:
            ratios.append(max_cost / est["cost_usd"])
        if total_tokens > 0:
            ratios.append(max_tokens / total_tokens)
        score = min([1.0, *ratios]) if ratios else 1.0

    parts = [
        f"total={total_tokens} (in={input_tokens}, out={output_tokens})",
        f"cost=${est['cost_usd']:.4f}",
        f"calls={calls}",
    ]
    if model:
        parts.append(f"model={model}")
    if cached_tokens:
        pct = cached_tokens / input_tokens * 100 if input_tokens else 0.0
        parts.append(f"cached={cached_tokens} ({pct:.1f}% of input)")
    if max_in_per_call:
        parts.append(f"max_in/call={max_in_per_call}")
    if used_fallback:
        parts.append("(fallback price)")
    if not budget_ok:
        parts.append("OVER BUDGET")

    return {
        "score": round(score, 4),
        "comment": "; ".join(parts),
        "extra": {
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cached_tokens": cached_tokens,
                "calls": calls,
                "model": model,
                "max_input_tokens_per_call": max_in_per_call,
                "p95_input_tokens_per_call": p95_in_per_call,
            },
            "cost_usd": est["cost_usd"],
            "input_price": est["input_price"],
            "output_price": est["output_price"],
            "used_fallback_price": est["used_fallback_price"],
            "budget": {"max_cost_usd": max_cost, "max_total_tokens": max_tokens},
            "elapsed_s": run_outputs.get("elapsed_s"),
        },
    }
