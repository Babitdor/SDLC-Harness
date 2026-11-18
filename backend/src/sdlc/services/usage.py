"""Token accounting for the live chat path.

Two facts drove this module, both measured from evaluation/results: 96% of this
pipeline's tokens are input tokens (6.22M in / 0.36M out on a single trial), and
cached_tokens was 0 across 199 model calls. The second number is the one worth
having a ledger for — an unmeasured cache is indistinguishable from a broken one,
and the first thing anyone does after enabling prompt caching is ask "did it work?".

So the job here is narrow: count what each model call actually reported, per
thread, and make cached_tokens visible.

Scope. Records every on_llm_end for the model instance it is attached to.
Because deepagents hands the *same* model object to the orchestrator and to every
delegated subagent, attaching one handler at construction covers all nested calls
— no per-node plumbing, and nothing is missed when a new subagent is added.

What is deliberately not here. The evaluation harness has its own, larger
extractor (harness_eval/usage_capture.py) that also computes reasoning tokens and
dollar cost from a price table. That belongs with the reports, not in the request
path, and the harness must stay importable without the backend runtime. The
shapes parsed below are the same, so the two sets of numbers stay comparable.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)

# Tracked threads are dropped oldest-first past this bound. Runs are short and
# threads are deleted explicitly; this only stops a long-lived process from
# accumulating one dict entry per conversation it ever served.
_MAX_TRACKED_THREADS = 256


def _as_int(value: Any) -> int:
    """Best-effort int coercion; anything unparseable counts as 0."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _model_name(llm_output: Any, generations: Any) -> str | None:
    """Read the model name out of an on_llm_end payload.

    Providers that omit it leave the ledger unable to say *which* model produced
    a number, which matters the moment a thread mixes models (model settings are
    read per chat session).
    """
    if isinstance(llm_output, dict):
        name = llm_output.get("model_name") or llm_output.get("model")
        if isinstance(name, str) and name:
            return name
    try:
        gens = generations or []
        if gens and gens[0]:
            message = getattr(gens[0][0], "message", None)
            meta = getattr(message, "response_metadata", None)
            if isinstance(meta, dict):
                name = meta.get("model_name") or meta.get("model")
                if isinstance(name, str) and name:
                    return name
    except Exception:  # noqa: BLE001 — payload shapes vary by provider
        pass
    return None


def extract_usage(llm_output: Any, generations: Any) -> dict[str, Any] | None:
    """Normalise one model call's usage into a flat dict, or None.

    Three shapes occur in practice, and a provider may report none of them
    (Ollama's OpenAI-compatible route omits cache detail entirely):

    * OpenAI-style llm_output["token_usage"] — prompt_tokens, completion_tokens,
      and prompt_tokens_details.cached_tokens for the prefix hits.
    * Anthropic-style llm_output["usage"] — input_tokens, output_tokens,
      cache_read_input_tokens.
    * langchain-normalised message.usage_metadata — input_tokens, output_tokens,
      input_token_details.cache_read.

    Cached tokens are a *subset* of input tokens, never additive: a call with 10k
    input and 8k cached is billed for 2k at full rate and 8k at the cache rate.
    """
    usage: dict[str, Any] = {}

    if isinstance(llm_output, dict):
        tu = llm_output.get("token_usage") or llm_output.get("usage")
        if isinstance(tu, dict):
            input_tokens = tu.get("prompt_tokens")
            if input_tokens is None:
                input_tokens = tu.get("input_tokens")
            output_tokens = tu.get("completion_tokens")
            if output_tokens is None:
                output_tokens = tu.get("output_tokens")
            total = tu.get("total_tokens")

            cached = tu.get("cache_read_input_tokens")
            if cached is None:
                details = tu.get("prompt_tokens_details") or tu.get("input_tokens_details")
                if isinstance(details, dict):
                    cached = details.get("cached_tokens")
                    if cached is None:
                        cached = details.get("cache_read")

            if input_tokens is not None or output_tokens is not None:
                usage["input_tokens"] = _as_int(input_tokens)
                usage["output_tokens"] = _as_int(output_tokens)
                usage["total_tokens"] = _as_int(total) or (
                    usage["input_tokens"] + usage["output_tokens"]
                )
                usage["cached_tokens"] = _as_int(cached)

    if "input_tokens" not in usage:
        try:
            gens = generations or []
            message = getattr(gens[0][0], "message", None) if gens and gens[0] else None
            meta = getattr(message, "usage_metadata", None)
            if isinstance(meta, dict) and (
                meta.get("input_tokens") is not None
                or meta.get("output_tokens") is not None
            ):
                details = meta.get("input_token_details") or {}
                cached = details.get("cache_read") if isinstance(details, dict) else 0
                if not cached and isinstance(details, dict):
                    cached = details.get("cached_tokens")
                usage["input_tokens"] = _as_int(meta.get("input_tokens"))
                usage["output_tokens"] = _as_int(meta.get("output_tokens"))
                usage["total_tokens"] = _as_int(meta.get("total_tokens")) or (
                    usage["input_tokens"] + usage["output_tokens"]
                )
                usage["cached_tokens"] = _as_int(cached)
        except Exception:  # noqa: BLE001 — payload shapes vary by provider
            pass

    if not usage:
        return None

    usage["model"] = _model_name(llm_output, generations)
    return usage


class _ThreadTotals:
    """Running totals for one thread. Plain object; the ledger owns the lock."""

    __slots__ = (
        "calls", "input_tokens", "output_tokens", "total_tokens",
        "cached_tokens", "max_input_tokens_per_call", "model",
    )

    def __init__(self) -> None:
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.cached_tokens = 0
        self.max_input_tokens_per_call = 0
        self.model: str | None = None

    def add(self, usage: dict[str, Any]) -> None:
        self.calls += 1
        self.input_tokens += usage.get("input_tokens", 0)
        self.output_tokens += usage.get("output_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)
        self.cached_tokens += usage.get("cached_tokens", 0)
        self.max_input_tokens_per_call = max(
            self.max_input_tokens_per_call, usage.get("input_tokens", 0)
        )
        if usage.get("model"):
            self.model = usage["model"]

    def snapshot(self, thread_id: str) -> dict[str, Any]:
        ratio = self.cached_tokens / self.input_tokens if self.input_tokens else 0.0
        return {
            "thread_id": thread_id,
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cached_tokens": self.cached_tokens,
            "cache_hit_ratio": round(ratio, 4),
            "max_input_tokens_per_call": self.max_input_tokens_per_call,
            "model": self.model,
        }


class UsageLedger:
    """Process-local per-thread token totals.

    Process-local for the same reason the session cache is: run state lives in
    api/app.py module globals, so a second worker would not see these numbers
    either. It is a diagnostic, never a billing record.
    """

    _totals: dict[str, _ThreadTotals] = {}
    _lock = threading.Lock()

    @classmethod
    def record(cls, thread_id: str, usage: dict[str, Any]) -> None:
        if not thread_id or not usage:
            return
        with cls._lock:
            totals = cls._totals.get(thread_id)
            if totals is None:
                if len(cls._totals) >= _MAX_TRACKED_THREADS:
                    cls._totals.pop(next(iter(cls._totals)), None)
                totals = cls._totals[thread_id] = _ThreadTotals()
            totals.add(usage)

    @classmethod
    def snapshot(cls, thread_id: str) -> dict[str, Any]:
        with cls._lock:
            totals = cls._totals.get(thread_id)
            if totals is None:
                return {
                    "thread_id": thread_id,
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cached_tokens": 0,
                    "cache_hit_ratio": 0.0,
                    "max_input_tokens_per_call": 0,
                    "model": None,
                }
            return totals.snapshot(thread_id)

    @classmethod
    def reset(cls, thread_id: str | None = None) -> None:
        with cls._lock:
            if thread_id is None:
                cls._totals.clear()
            else:
                cls._totals.pop(thread_id, None)


class UsageRecordingHandler(BaseCallbackHandler):
    """Record every model call this instance is attached to.

    Attached to the *model*, not to a graph config: deepagents passes one model
    instance down to the orchestrator and all subagents, so this single handler
    sees every call in the run, including nested subagent ones. A config-level
    callback would also cover them, but would need re-plumbing at each invoke
    site and would silently miss any future site that forgot.
    """

    # Accounting must never break a run: a raising handler would abort the call.
    raise_error = False

    def __init__(self, thread_id: str) -> None:
        self.thread_id = thread_id

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Extract and record usage; never raise into the model path."""
        try:
            llm_output = getattr(response, "llm_output", None)
            generations = getattr(response, "generations", None)
            usage = extract_usage(llm_output, generations)
            if usage is None:
                return
            UsageLedger.record(self.thread_id, usage)
            logger.debug(
                "model call thread=%s in=%d out=%d cached=%d",
                self.thread_id,
                usage["input_tokens"],
                usage["output_tokens"],
                usage["cached_tokens"],
            )
        except Exception:  # noqa: BLE001 — accounting must never break a run
            logger.debug(
                "Usage capture failed for thread %s", self.thread_id, exc_info=True
            )
