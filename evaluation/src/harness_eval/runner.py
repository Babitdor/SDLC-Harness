"""Evaluator registry for SDLC Harness evaluation.

Evaluators are registered via the ``@register`` decorator and looked up by
name. The filesystem task harness (``harness_eval.tasks``) dispatches them
directly — no LangSmith dependency.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# LangSmith's ``EvaluationResult`` is ``extra="forbid"``: a returned dict with
# any unknown top-level key (e.g. ``dimension_scores``, ``metrics``) fails
# coercion and the evaluator's feedback is silently dropped — it renders empty.
# Fold non-standard keys into the sanctioned ``extra`` field so evaluators can
# return rich breakdowns without breaking. Defends every current and future
# evaluator, not just the two that hit this.
_ALLOWED_RESULT_KEYS = frozenset({
    "key", "score", "value", "comment", "correction",
    "evaluator_info", "feedback_config", "source_run_id",
    "target_run_id", "extra",
})


def _normalize_result(result: Any) -> Any:
    """Move any non-standard top-level keys of an evaluator dict into ``extra``."""
    if not isinstance(result, dict):
        return result
    extras = {k: result[k] for k in result if k not in _ALLOWED_RESULT_KEYS}
    if not extras:
        return result
    cleaned = {k: v for k, v in result.items() if k in _ALLOWED_RESULT_KEYS}
    cleaned["extra"] = {**(cleaned.get("extra") or {}), **extras}
    return cleaned


def _standardize_evaluator(fn: Callable) -> Callable:
    """Wrap an evaluator so its result always satisfies LangSmith's schema.

    Preserves the function name (LangSmith uses it as the feedback key) and the
    sync/async nature of the original.
    """
    if asyncio.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def _async_wrapper(*args, **kwargs):
            return _normalize_result(await fn(*args, **kwargs))

        return _async_wrapper

    @functools.wraps(fn)
    def _wrapper(*args, **kwargs):
        return _normalize_result(fn(*args, **kwargs))

    return _wrapper

# ── Evaluator registry ──────────────────────────────────────────────────
# Maps evaluator names to their callable functions. Used by the CLI to
# resolve --evaluator arguments.

_EVALUATOR_REGISTRY: dict[str, Callable] = {}


def register(name: str) -> Callable:
    """Decorator to register an evaluator function."""

    def decorator(fn: Callable) -> Callable:
        _EVALUATOR_REGISTRY[name] = fn
        return fn

    return decorator


def get_evaluator(name: str) -> Callable | None:
    """Look up an evaluator by name."""
    return _EVALUATOR_REGISTRY.get(name)


def list_evaluators() -> list[str]:
    """Return all registered evaluator names."""
    return sorted(_EVALUATOR_REGISTRY.keys())


# ── Register built-in evaluators ────────────────────────────────────────
# The harness evaluation measures cost and process only. Artefact-quality
# graders were removed; do not add them back here.

@register("cost-tokens")
def _cost_tokens():
    from harness_eval.evaluators.cost_tokens_eval import cost_tokens_evaluator

    return cost_tokens_evaluator


@register("process-metrics")
def _process_metrics():
    from harness_eval.evaluators.process_metrics_eval import (
        process_metrics_evaluator,
    )

    return process_metrics_evaluator
