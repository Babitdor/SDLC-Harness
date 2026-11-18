"""Token-usage capture for the SDLC evaluation harness.

Wraps two ways of getting token counts out of a pipeline run:

1. **Callback handler** (primary, comprehensive): a ``BaseCallbackHandler``
   that records usage from every model ``on_llm_end``. This captures the
   orchestrator *and* all nested subagent model calls, so the totals include
   every LLM invocation in the run, not just the final message.
2. **Result-message fallback**: summing ``usage_metadata`` from the messages in
   the graph result. Less complete (only the final message chain), used when a
   callback cannot be attached.

The captured records are plain dicts so they survive serialisation into the
task-suite JSON report.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


def _extract_cached_tokens(tu: dict | None, um: dict | None) -> int:
    """Pull the cached (prompt-cache read) input token count out of a payload.

    96% of this pipeline's tokens are input, and ~71 calls per trial re-send
    a largely identical prefix — the textbook prompt-caching case. Without
    this we cannot tell whether caching is already active (in which case the
    cost estimate is overstated, since cached input bills at a fraction of
    the normal rate) or absent (in which case the biggest available cost
    lever is untouched *and* unmeasurable after enabling it).

    Providers report it under different keys:

    * OpenAI-style ``token_usage`` → ``prompt_tokens_details.cached_tokens``.
    * Anthropic-style ``usage`` → ``cache_read_input_tokens``.
    * langchain-normalised ``usage_metadata`` →
      ``input_token_details.cache_read``.

    Cached tokens are a subset of ``input_tokens``, never additional to them.
    """
    if isinstance(tu, dict):
        val = tu.get("cache_read_input_tokens")
        if isinstance(val, (int, float)) and val > 0:
            return int(val)
        details = tu.get("prompt_tokens_details") or tu.get("input_tokens_details")
        if isinstance(details, dict):
            val = details.get("cached_tokens") or details.get("cache_read")
            if isinstance(val, (int, float)) and val > 0:
                return int(val)

    if isinstance(um, dict):
        details = um.get("input_token_details")
        if isinstance(details, dict):
            val = details.get("cache_read") or details.get("cached_tokens")
            if isinstance(val, (int, float)) and val > 0:
                return int(val)
    return 0


def _extract_model_name(llm_output: Any, generations: Any) -> str | None:
    """Pull the model name out of an ``on_llm_end`` payload.

    Without this ``usage["model"]`` was structurally always ``None``: the
    handler never recorded a name, so ``get_prices(None)`` fell back on every
    single call and the whole ``PRICES`` table was dead code on this path.
    Every dollar figure then rested on the fallback rate regardless of which
    model actually ran.

    Two shapes, matching the usage extractor: OpenAI-style ``llm_output``
    carries ``model_name`` (sometimes ``model``); the langchain-normalised
    generation carries it on the message's ``response_metadata``.
    """
    if isinstance(llm_output, dict):
        name = llm_output.get("model_name") or llm_output.get("model")
        if isinstance(name, str) and name:
            return name
    try:
        gens = generations or []
        if gens and gens[0]:
            msg = getattr((gens[0][0] if len(gens[0]) else None), "message", None)
            meta = getattr(msg, "response_metadata", None)
            if isinstance(meta, dict):
                name = meta.get("model_name") or meta.get("model")
                if isinstance(name, str) and name:
                    return name
    except Exception:  # pragma: no cover - defensive against odd shapes
        pass
    return None


def _extract_reasoning_tokens(tu: dict | None, um: dict | None) -> int:
    """Pull the reasoning/thinking token count out of a usage payload.

    Providers report it under different keys:

    * OpenAI-style ``token_usage`` → ``completion_tokens_details.reasoning_tokens``
      (the o-series "thinking" budget).
    * Anthropic-style ``llm_output["usage"]`` → ``output_tokens`` where
      ``output_tokens_details.reasoning_tokens`` is also set.
    * langchain-normalised ``usage_metadata`` → ``output_token_details.reasoning``
      (older ``input_token_details``/``output_token_details`` carry ``reasoning``).

    Reasoning is a strict subset of the completion/output tokens (it is the
    portion spent on internal thinking before the visible answer), so it is
    reported in addition to — never instead of — ``output_tokens``.
    """
    for holder, keys in ((tu, ("completion_tokens_details", "output_tokens_details")),):
        if not isinstance(holder, dict):
            continue
        for key in keys:
            details = holder.get(key)
            if isinstance(details, dict):
                val = details.get("reasoning_tokens") or details.get("reasoning")
                if isinstance(val, (int, float)) and val > 0:
                    return int(val)

    if isinstance(um, dict):
        for key in ("output_token_details", "input_token_details"):
            details = um.get(key)
            if isinstance(details, dict):
                val = details.get("reasoning")
                if isinstance(val, (int, float)) and val > 0:
                    return int(val)
    return 0


def _usage_from_llm_end(llm_output: Any, generations: Any) -> dict[str, Any] | None:
    """Extract a usage dict from an ``on_llm_end`` payload.

    Two shapes appear across providers:
      * ``llm_output.get("token_usage")`` (OpenAI-style) with
        ``prompt_tokens`` / ``completion_tokens`` / ``total_tokens``.
      * ``generations[0][0].message.usage_metadata`` (langchain-normalised)
        with ``input_tokens`` / ``output_tokens`` / ``total_tokens``.

    Returns a normalised
    ``{"input_tokens", "output_tokens", "total_tokens", "reasoning_tokens",
    "cached_tokens"}`` dict, or None when no usage was reported.
    """
    tu = None
    um = None
    if isinstance(llm_output, dict):
        tu = llm_output.get("token_usage")
        if not isinstance(tu, dict):
            # Anthropic's ChatAnthropic reports llm_output["usage"] directly.
            tu = llm_output.get("usage")

    if isinstance(tu, dict) and (
        tu.get("prompt_tokens") is not None or tu.get("input_tokens") is not None
    ):
        return {
            "input_tokens": int(tu.get("input_tokens") or tu.get("prompt_tokens") or 0),
            "output_tokens": int(
                tu.get("output_tokens") or tu.get("completion_tokens") or 0
            ),
            "total_tokens": int(
                tu.get("total_tokens")
                or (tu.get("input_tokens") or tu.get("prompt_tokens") or 0)
                + (tu.get("output_tokens") or tu.get("completion_tokens") or 0)
            ),
            "reasoning_tokens": _extract_reasoning_tokens(tu, None),
            "cached_tokens": _extract_cached_tokens(tu, None),
        }

    try:
        gens = generations or []
        if gens and gens[0]:
            um = getattr((gens[0][0] if len(gens[0]) else None), "message", None)
            um = getattr(um, "usage_metadata", None)
    except Exception:  # pragma: no cover - defensive against odd shapes
        um = None

    if isinstance(um, dict) and um.get("input_tokens") is not None:
        return {
            "input_tokens": int(um.get("input_tokens") or 0),
            "output_tokens": int(um.get("output_tokens") or 0),
            "total_tokens": int(um.get("total_tokens") or 0),
            "reasoning_tokens": _extract_reasoning_tokens(None, um),
            "cached_tokens": _extract_cached_tokens(None, um),
        }

    return None


def _percentile(sorted_values: list[int], pct: int) -> int:
    """Nearest-rank percentile of an already-sorted list (0 when empty)."""
    if not sorted_values:
        return 0
    idx = max(0, min(len(sorted_values) - 1, round(pct / 100 * len(sorted_values)) - 1))
    return sorted_values[idx]


class UsageCaptureHandler(BaseCallbackHandler):
    """Accumulate token usage across every model call in a run.

    Attach to the graph invoke config via ``config["callbacks"]``. After the
    run, read :attr:`records` (one per LLM call), :attr:`totals`, and
    :attr:`invocations` (the strict count of every ``on_llm_end``).
    """

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self.invocations: int = 0
        self.totals: dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "reasoning_tokens": 0,
            "cached_tokens": 0,
        }

    def on_llm_end(self, response, **kwargs) -> None:  # noqa: N802 (langchain API)
        # Strict invocation counter: every completed model call counts, even
        # when the provider reported no usage (cached / non-token providers).
        self.invocations += 1
        try:
            usage = _usage_from_llm_end(
                getattr(response, "llm_output", None),
                getattr(response, "generations", None),
            )
            if usage is not None:
                usage["model"] = _extract_model_name(
                    getattr(response, "llm_output", None),
                    getattr(response, "generations", None),
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to read llm usage: %s", exc)
            return
        if not usage:
            return
        self.records.append(usage)
        for key in self.totals:
            self.totals[key] += usage.get(key, 0)

    def summarize(self, model: str | None = None) -> dict[str, Any]:
        """Return a compact usage summary for the evaluator / report.

        Includes the per-call input-token distribution. Only totals used to
        be persisted, which made it impossible to check whether the context
        ever approached the summarization trigger (0.85 x the declared
        context window): a mean of ~15K/call is equally consistent with a
        flat 15K context and with a handful of 109K calls hidden among many
        small ones. ``max_input_tokens_per_call`` settles it directly.
        """
        records = self.records or []
        per_call_input = sorted(int(r.get("input_tokens") or 0) for r in records)
        return {
            "input_tokens": self.totals["input_tokens"],
            "output_tokens": self.totals["output_tokens"],
            "total_tokens": self.totals["total_tokens"],
            "reasoning_tokens": self.totals["reasoning_tokens"],
            # Subset of input_tokens that was served from the prompt cache.
            # 0 means either "no caching" or "provider does not report it".
            "cached_tokens": self.totals["cached_tokens"],
            "calls": len(records),
            "invocations": self.invocations,
            "model": model or (records[0].get("model") if records else None),
            "max_input_tokens_per_call": per_call_input[-1] if per_call_input else 0,
            "p95_input_tokens_per_call": _percentile(per_call_input, 95),
        }


def usage_from_messages(messages: Any) -> dict[str, Any]:
    """Sum ``usage_metadata`` across a list of langchain messages.

    A less complete fallback than the callback handler: it only sees the final
    message chain of the top-level result, not nested subagent calls.
    """
    input_tokens = output_tokens = total_tokens = reasoning_tokens = 0
    cached_tokens = 0
    model: str | None = None
    if isinstance(messages, (list, tuple)):
        for msg in messages:
            um = getattr(msg, "usage_metadata", None)
            if isinstance(um, dict):
                input_tokens += um.get("input_tokens") or 0
                output_tokens += um.get("output_tokens") or 0
                total_tokens += um.get("total_tokens") or 0
                reasoning_tokens += _extract_reasoning_tokens(None, um)
                cached_tokens += _extract_cached_tokens(None, um)
            if model is None:
                model = getattr(msg, "response_metadata", {}).get("model_name")
    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "total_tokens": int(total_tokens),
        "reasoning_tokens": int(reasoning_tokens),
        "cached_tokens": int(cached_tokens),
        "model": model,
    }
