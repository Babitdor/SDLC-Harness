"""Usage extractor and ledger: what the cache actually saved.

The number that matters is cached_tokens. Measured before this existed:
6,224,330 input tokens across 199 calls on one trial, cached_tokens = 0.
Everything here exists so that number stops being invisible.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sdlc.services.usage import (
    UsageLedger,
    UsageRecordingHandler,
    extract_usage,
)


@pytest.fixture(autouse=True)
def _clean_ledger():
    UsageLedger.reset()
    yield
    UsageLedger.reset()


def test_openai_style_usage_and_cache_detail() -> None:
    usage = extract_usage(
        {
            "token_usage": {
                "prompt_tokens": 10_000,
                "completion_tokens": 200,
                "total_tokens": 10_200,
                "prompt_tokens_details": {"cached_tokens": 8_192},
            },
            "model_name": "gpt-5",
        },
        None,
    )

    assert usage is not None
    assert usage["input_tokens"] == 10_000
    assert usage["output_tokens"] == 200
    assert usage["cached_tokens"] == 8_192
    assert usage["model"] == "gpt-5"
    # Cached tokens are a SUBSET of input. Adding them would double-count the
    # prefix and inflate the saving the ledger reports.
    assert usage["total_tokens"] == 10_200


def test_anthropic_style_cache_read_is_read() -> None:
    usage = extract_usage(
        {
            "usage": {
                "input_tokens": 4_000,
                "output_tokens": 100,
                "cache_read_input_tokens": 3_500,
            }
        },
        None,
    )

    assert usage is not None
    assert usage["cached_tokens"] == 3_500
    assert usage["total_tokens"] == 4_100


def test_usage_metadata_fallback_when_llm_output_is_empty() -> None:
    """Ollama-style endpoints report nothing in llm_output; the message does."""
    message = SimpleNamespace(
        usage_metadata={
            "input_tokens": 900,
            "output_tokens": 30,
            "total_tokens": 930,
            "input_token_details": {"cache_read": 512},
        },
        response_metadata={"model_name": "deepseek-v4-flash"},
    )
    generations = [[SimpleNamespace(message=message)]]

    usage = extract_usage({}, generations)

    assert usage is not None
    assert usage["input_tokens"] == 900
    assert usage["cached_tokens"] == 512
    assert usage["model"] == "deepseek-v4-flash"


def test_no_usage_reported_stays_none() -> None:
    """A provider that reports nothing must not be counted as zero tokens."""
    assert extract_usage({}, None) is None
    assert extract_usage(None, []) is None


def test_ledger_accumulates_and_reports_hit_ratio() -> None:
    UsageLedger.record("t1", {"input_tokens": 1000, "output_tokens": 10,
                              "total_tokens": 1010, "cached_tokens": 900,
                              "model": "m"})
    UsageLedger.record("t1", {"input_tokens": 500, "output_tokens": 20,
                              "total_tokens": 520, "cached_tokens": 0,
                              "model": "m"})

    snap = UsageLedger.snapshot("t1")
    assert snap["calls"] == 2
    assert snap["input_tokens"] == 1500
    assert snap["output_tokens"] == 30
    assert snap["cached_tokens"] == 900
    assert snap["max_input_tokens_per_call"] == 1000
    assert snap["cache_hit_ratio"] == 0.6


def test_ledger_snapshot_of_unknown_thread_is_zeroed() -> None:
    snap = UsageLedger.snapshot("never-seen")
    assert snap["calls"] == 0
    assert snap["cache_hit_ratio"] == 0.0
    assert snap["model"] is None


def test_handler_records_from_a_response_object() -> None:
    handler = UsageRecordingHandler("t2")
    response = SimpleNamespace(
        llm_output={
            "token_usage": {
                "prompt_tokens": 2000,
                "completion_tokens": 50,
                "prompt_tokens_details": {"cached_tokens": 1536},
            }
        },
        generations=[],
    )

    handler.on_llm_end(response)

    snap = UsageLedger.snapshot("t2")
    assert snap["calls"] == 1
    assert snap["cached_tokens"] == 1536
    assert snap["cache_hit_ratio"] == 0.768


def test_handler_never_raises_into_the_model_path() -> None:
    """Accounting is a diagnostic; it must not be able to break a chat."""

    class _Broken:
        @property
        def llm_output(self):
            raise RuntimeError("provider returned garbage")

    handler = UsageRecordingHandler("t3")
    handler.on_llm_end(_Broken())  # must not raise
    assert UsageLedger.snapshot("t3")["calls"] == 0


def test_ledger_bounds_tracked_threads() -> None:
    """A long-lived process must not accumulate one entry per conversation."""
    from sdlc.services import usage as usage_mod

    limit = usage_mod._MAX_TRACKED_THREADS
    for i in range(limit + 5):
        UsageLedger.record(f"thread-{i}", {"input_tokens": 1, "output_tokens": 1,
                                            "total_tokens": 2, "cached_tokens": 0})

    assert len(UsageLedger._totals) == limit
    # Oldest first out: the most recent threads are the ones still running.
    assert UsageLedger.snapshot(f"thread-{limit + 4}")["calls"] == 1
