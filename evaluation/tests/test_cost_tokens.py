"""Tests for the cost/token measurement pipeline.

All deterministic, no Docker / model creds: covers the price-table math, the
budget-aware evaluator scoring, the callback usage capture, and registry wiring.
"""

from __future__ import annotations

import asyncio

from harness_eval.costs import DEFAULT_PRICE, estimate_cost, get_prices
from harness_eval.evaluators.cost_tokens_eval import cost_tokens_evaluator
from harness_eval.usage_capture import (
    UsageCaptureHandler,
    usage_from_messages,
    _usage_from_llm_end,
)


# ── prices / cost math ──────────────────────────────────────────────────────

def test_price_lookup_matches_substring():
    assert get_prices("gpt-4o-2024-08-06") == ({"input": 2.50, "output": 10.00}, False)
    assert get_prices("meta-llama/Llama-3.1-70B")[0] == {"input": 0.88, "output": 0.88}
    # most-specific wins when multiple keys are substrings
    assert get_prices("gpt-4.1-mini")[0] == {"input": 0.40, "output": 1.60}


def test_price_lookup_fallback_for_unknown():
    prices, fallback = get_prices("my-self-hosted-model")
    assert fallback is True
    assert prices == DEFAULT_PRICE
    # None model also falls back
    assert get_prices(None)[1] is True


def test_estimate_cost_math():
    # gpt-4o: 1M input @ $2.50, 1M output @ $10.00
    est = estimate_cost(1_000_000, 500_000, "gpt-4o")
    assert est["cost_usd"] == 2.50 + 5.00
    assert est["input_tokens"] == 1_000_000
    assert est["output_tokens"] == 500_000
    assert est["used_fallback_price"] is False


def test_estimate_cost_zero_tokens():
    est = estimate_cost(0, 0, "gpt-4o")
    assert est["cost_usd"] == 0.0


def test_estimate_cost_with_explicit_prices():
    est = estimate_cost(10_000, 5_000, None, prices={"input": 1.0, "output": 2.0})
    assert est["cost_usd"] == 0.010 + 0.010  # 10k/1M*1 + 5k/1M*2
    assert est["used_fallback_price"] is False  # explicit prices beat table


# ── usage capture ───────────────────────────────────────────────────────────

def test_extract_usage_from_token_usage_dict():
    # OpenAI-style llm_output.token_usage
    usage = _usage_from_llm_end({"token_usage": {"prompt_tokens": 100, "completion_tokens": 40}}, None)
    assert usage == {
        "input_tokens": 100, "output_tokens": 40, "total_tokens": 140,
        "reasoning_tokens": 0, "cached_tokens": 0,
    }


def test_extract_usage_from_generation_usage_metadata():
    # langchain-normalised generations -> message.usage_metadata
    class _Msg:
        usage_metadata = {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10}

    class _Gen:
        message = _Msg()

    usage = _usage_from_llm_end(None, [[_Gen()]])
    assert usage["input_tokens"] == 7 and usage["output_tokens"] == 3
    assert usage["reasoning_tokens"] == 0


def test_usage_handler_accumulates_across_calls():
    handler = UsageCaptureHandler()

    # simulate two LLM calls
    handler.on_llm_end(_FakeResponse(tu={"prompt_tokens": 100, "completion_tokens": 40}), **{})
    handler.on_llm_end(_FakeResponse(tu={"prompt_tokens": 50, "completion_tokens": 10}), **{})

    assert handler.totals == {
        "input_tokens": 150, "output_tokens": 50, "total_tokens": 200,
        "reasoning_tokens": 0, "cached_tokens": 0,
    }
    assert len(handler.records) == 2
    summary = handler.summarize(model="gpt-4o")
    assert summary["total_tokens"] == 200 and summary["calls"] == 2 and summary["model"] == "gpt-4o"


def test_usage_handler_ignores_no_usage():
    handler = UsageCaptureHandler()
    handler.on_llm_end(_FakeResponse(tu=None), **{})
    handler.on_llm_end(_FakeResponse(tu={}), **{})
    assert handler.totals["total_tokens"] == 0
    assert handler.records == []


def test_usage_from_messages_fallback():
    class _Msg:
        def __init__(self, um):
            self.usage_metadata = um
            self.response_metadata = {"model_name": "gpt-4o"}

    messages = [_Msg({"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})]
    out = usage_from_messages(messages)
    assert out["total_tokens"] == 15 and out["model"] == "gpt-4o"


# ── evaluator ───────────────────────────────────────────────────────────────

def _run(usage: dict, elapsed_s: float = 1.0) -> dict:
    return {"outputs": {"usage": usage, "elapsed_s": elapsed_s}}


def test_cost_tokens_evaluator_in_budget():
    out = cost_tokens_evaluator(
        _run({"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500, "calls": 4, "model": "gpt-4o"}),
        {"inputs": {}},
    )
    assert out["score"] == 1.0, out
    assert out["extra"]["cost_usd"] > 0
    assert out["extra"]["usage"]["total_tokens"] == 1500
    assert out["extra"]["usage"]["calls"] == 4
    assert "gpt-4o" in out["comment"]


def test_cost_tokens_evaluator_over_token_budget():
    # gpt-4o at ~150k total tokens (in=100k, out=50k) ≈ $0.75, under default $1 cost
    # but over the default 200k? no — force a tiny token budget.
    out = cost_tokens_evaluator(
        _run({"input_tokens": 100_000, "output_tokens": 50_000, "total_tokens": 150_000, "calls": 4, "model": "gpt-4o"}),
        {"inputs": {"max_total_tokens": 100_000}},
    )
    assert out["score"] < 1.0, out
    assert out["extra"]["cost_usd"] == 0.75  # 100k*2.5/1M + 50k*10/1M
    assert "OVER BUDGET" in out["comment"]


def test_cost_tokens_evaluator_no_usage_scores_budget_ok():
    # no usage reported -> cost 0, within budget -> score 1.0 but calls 0
    out = cost_tokens_evaluator(_run({}), {"inputs": {}})
    assert out["score"] == 1.0
    assert out["extra"]["usage"]["total_tokens"] == 0


# ── R3 dual-cap semantics (flag and score share one budget envelope) ───────

def test_cost_tokens_evaluator_token_breach_only_scores_below_1():
    """Cost under the $1 cap but tokens over their cap: OVER flag fires AND
    score < 1.0 (old code flagged OVER while the score still looked only at
    cost, so a cheap-but-token-heavy trial could score 0.9+ and read as 'fine')."""
    out = cost_tokens_evaluator(
        _run({"input_tokens": 100_000, "output_tokens": 50_000, "total_tokens": 150_000, "calls": 4, "model": "gpt-4o"}),
        {"inputs": {"max_total_tokens": 100_000}},
    )
    assert "OVER BUDGET" in out["comment"]
    assert out["score"] < 1.0
    # cap/cost = 1.00/0.75 = 1.333 (clamped away, cost is in budget);
    # cap/tokens = 100k/150k = 0.667 -> tokens is the binding breach.
    assert abs(out["score"] - (100_000 / 150_000)) < 1e-4


def test_cost_tokens_evaluator_cost_breach_only_scores_below_1():
    """Tokens under the cap but cost over it: OVER fires and score reflects
    the token ratio (the non-breached cap still pins score < 1.0)."""
    out = cost_tokens_evaluator(
        _run({"input_tokens": 1_400_000, "output_tokens": 20_000, "total_tokens": 1_420_000, "calls": 30, "model": "gpt-4o"}),
        {"inputs": {"max_cost_usd": 2.0, "max_total_tokens": 1_500_000}},
    )
    assert "OVER BUDGET" in out["comment"]
    assert out["score"] < 1.0
    # cost = 1.4M*2.5 + 20k*10 = 3.5 + 0.2 = $3.70 -> cap/cost = 2.0/3.7 = 0.541
    # cap/tokens = 1.5M/1.42M = 1.056 (clamped away) -> cost is the binding breach.
    assert abs(out["score"] - (2.0 / 3.70)) < 1e-4


def test_cost_tokens_evaluator_raised_default_no_spurious_flag():
    """The new default token cap (1.5M) matches real consumption: a realistic
    trial (1.1M tokens, cost under $1) is NOT flagged OVER — the old 200K cap
    flagged every trial purely on tokens (~5x under real usage)."""
    out = cost_tokens_evaluator(
        _run({"input_tokens": 1_050_000, "output_tokens": 50_000, "total_tokens": 1_100_000, "calls": 71, "model": "llama-3.1-70b"}),
        {"inputs": {}},  # defaults: max_cost_usd=1.0, max_total_tokens=1_500_000
    )
    # cost = 1.1M * 0.88 / 1M = $0.968 < $1.00 and 1.1M < 1.5M -> in budget
    assert out["score"] == 1.0, out
    assert "OVER BUDGET" not in out["comment"]


def test_cost_tokens_evaluator_double_breach_scores_worst():
    """Both caps breached: the score must be the WORST in the suite, not the best.

    This case previously asserted ``score == 1.0`` — the old actual/cap form
    rose with overage and clamped, so a 10x-over-budget trial scored the same
    as an in-budget one. Measured on the 20-trial batch, r(cost, score) was
    +0.890: the grader rewarded expensive runs.
    """
    out = cost_tokens_evaluator(
        _run({"input_tokens": 2_000_000, "output_tokens": 500_000, "total_tokens": 2_500_000, "calls": 4, "model": "gpt-4o"}),
        {"inputs": {"max_cost_usd": 1.0, "max_total_tokens": 1_500_000}},
    )
    assert "OVER BUDGET" in out["comment"]
    # cost = $10.00 -> cap/cost = 0.10; tokens 2.5M -> cap/tokens = 0.60.
    # Binding breach is cost.
    assert abs(out["score"] - 0.10) < 1e-4


def test_cost_tokens_score_falls_monotonically_with_cost():
    """Property guard: more overage must never score higher.

    This is the invariant the old formula violated, and the one no
    single-case assertion caught.
    """
    budget = {"inputs": {"max_cost_usd": 1.0, "max_total_tokens": 1_500_000}}
    scores = []
    for in_tok in (400_000, 800_000, 1_200_000, 2_000_000, 4_000_000):
        out = cost_tokens_evaluator(
            _run({
                "input_tokens": in_tok, "output_tokens": 0,
                "total_tokens": in_tok, "calls": 10, "model": "gpt-4o",
            }),
            budget,
        )
        scores.append(out["score"])

    assert scores == sorted(scores, reverse=True), scores
    assert scores[-1] < scores[0]


# ── registry wiring ─────────────────────────────────────────────────────────

def test_cost_tokens_registered():
    from harness_eval.runner import get_evaluator, list_evaluators

    assert get_evaluator("cost-tokens") is not None
    assert "cost-tokens" in list_evaluators()


def test_cost_tokens_dispatches_via_grade():
    """The filesystem task-suite grader dispatch resolves cost-tokens."""
    from pathlib import Path

    from harness_eval.tasks.loader import GraderSpec, load_task
    from harness_eval.tasks.runner import _grade

    task = load_task(Path(__file__).resolve().parents[1] / "dataset" / "Task-25")
    spec = GraderSpec(name="cost-tokens")
    outputs = {"usage": {"input_tokens": 500, "output_tokens": 50, "total_tokens": 550, "calls": 2, "model": "gpt-4o"}}
    res = asyncio.run(_grade(task, spec, {"request": task.prompt}, outputs))
    assert isinstance(res.get("score"), (int, float)), res
    assert "cost" in (res.get("comment") or "").lower()


class _FakeResponse:
    """Minimal stand-in for the langchain on_llm_end ``response``."""

    def __init__(self, tu, model=None):
        self.llm_output = {"token_usage": tu} if tu else None
        if self.llm_output is not None and model:
            self.llm_output["model_name"] = model
        self.generations = None


# ── P2: the fallback flag must survive resolved prices ─────────────────────

def test_estimate_cost_forwards_explicit_fallback_flag():
    """A caller that resolves fallback prices itself can say so.

    Passing resolved prices in used to reset the flag to False, so every
    fallback-priced run was stamped ``used_fallback_price: false`` while its
    own comment read ``(fallback price)``.
    """
    prices, used_fallback = get_prices("some-unlisted-model")
    assert used_fallback is True

    est = estimate_cost(1_000_000, 0, "some-unlisted-model",
                        prices=prices, used_fallback=used_fallback)
    assert est["used_fallback_price"] is True

    # Omitting the flag keeps the old behaviour for genuine overrides.
    est2 = estimate_cost(1_000_000, 0, "gpt-4o", prices={"input": 1.0, "output": 2.0})
    assert est2["used_fallback_price"] is False


def test_cost_tokens_evaluator_reports_fallback_price_truthfully():
    """The grader's machine-readable flag must agree with its own comment."""
    out = cost_tokens_evaluator(
        # deliberately a model with no PRICES entry — deepseek-v4-flash is
        # priced now, so it no longer exercises the fallback path.
        _run({"input_tokens": 1000, "output_tokens": 100, "total_tokens": 1100,
              "calls": 2, "model": "some-unlisted-local-model"}),
        {"inputs": {}},
    )
    assert "(fallback price)" in out["comment"]
    assert out["extra"]["used_fallback_price"] is True


# ── P3: the model name must reach the summary ──────────────────────────────

def test_usage_handler_captures_model_name_from_llm_output():
    """Without this ``usage['model']`` was structurally always None, so
    get_prices() fell back on every call and PRICES was dead code."""
    handler = UsageCaptureHandler()
    handler.on_llm_end(
        _FakeResponse(tu={"prompt_tokens": 10, "completion_tokens": 5}, model="gpt-4o"),
        **{},
    )
    assert handler.records[0]["model"] == "gpt-4o"
    # summarize() with no explicit override picks it up from the records
    assert handler.summarize()["model"] == "gpt-4o"


def test_usage_handler_captures_model_name_from_response_metadata():
    """langchain-normalised shape: name lives on the message metadata."""
    class _Msg:
        usage_metadata = {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10}
        response_metadata = {"model_name": "claude-3-5-sonnet-20241022"}

    class _Gen:
        message = _Msg()

    class _Resp:
        llm_output = None
        generations = [[_Gen()]]

    handler = UsageCaptureHandler()
    handler.on_llm_end(_Resp(), **{})
    assert handler.summarize()["model"] == "claude-3-5-sonnet-20241022"


# ── P4: per-call input distribution ────────────────────────────────────────

def test_summarize_reports_per_call_input_distribution():
    """Totals alone cannot tell a flat 15K context from a few 109K calls
    hidden among many small ones — which is exactly what deciding whether
    summarization ever fires depends on."""
    handler = UsageCaptureHandler()
    for prompt_tokens in (1_000, 2_000, 3_000, 120_000):
        handler.on_llm_end(
            _FakeResponse(tu={"prompt_tokens": prompt_tokens, "completion_tokens": 1}),
            **{},
        )

    summary = handler.summarize()
    assert summary["max_input_tokens_per_call"] == 120_000
    assert summary["p95_input_tokens_per_call"] == 120_000
    # the mean would have been ~31.5K and hidden the 120K call entirely
    assert summary["input_tokens"] / summary["calls"] < 40_000


def test_summarize_per_call_distribution_empty_run():
    assert UsageCaptureHandler().summarize()["max_input_tokens_per_call"] == 0


# ── P5: cached input tokens ────────────────────────────────────────────────

def test_extract_cached_tokens_openai_shape():
    usage = _usage_from_llm_end(
        {"token_usage": {"prompt_tokens": 1000, "completion_tokens": 10,
                         "prompt_tokens_details": {"cached_tokens": 900}}},
        None,
    )
    assert usage["cached_tokens"] == 900


def test_extract_cached_tokens_anthropic_shape():
    usage = _usage_from_llm_end(
        {"usage": {"input_tokens": 1000, "output_tokens": 10,
                   "cache_read_input_tokens": 750}},
        None,
    )
    assert usage["cached_tokens"] == 750


def test_cached_tokens_default_zero_when_unreported():
    """0 means 'no caching OR provider does not report it' — never a crash."""
    usage = _usage_from_llm_end(
        {"token_usage": {"prompt_tokens": 100, "completion_tokens": 40}}, None
    )
    assert usage["cached_tokens"] == 0


# ── P6: the cost eval must not reward a degraded run ───────────────────────

# ── Ollama Cloud rate table (researched 2026-08-27) ────────────────────────

def test_ollama_cloud_models_resolve_to_real_rates():
    """The tags the harness actually runs must not hit DEFAULT_PRICE.

    `:cloud` suffixes and dotted versions still have to match.
    """
    for tag, expect in [
        ("deepseek-v4-flash:cloud", {"input": 0.22, "output": 0.66}),
        ("minimax-m3:cloud", {"input": 0.30, "output": 1.20}),
        ("kimi-k3:cloud", {"input": 3.00, "output": 15.00}),
        ("mistral-large-3:cloud", {"input": 0.50, "output": 1.50}),
    ]:
        prices, fallback = get_prices(tag)
        assert fallback is False, f"{tag} fell back to the placeholder rate"
        assert prices == expect, tag


def test_specific_model_keys_are_not_shadowed_by_generic_ones():
    """Substring matching returns the FIRST key that matches, so the specific
    Ollama-cloud entries must be declared before the older generic ones.

    Without that ordering `qwen3.5` hits the generic `qwen3` entry and
    `minimax-m2.7` hits the generic `minimax` entry — both wrong, and both
    silent (used_fallback stays False, so nothing flags it).
    """
    assert get_prices("qwen3.5-flash:cloud")[0] == {"input": 0.10, "output": 0.40}
    assert get_prices("qwen3.5-plus")[0] == {"input": 0.40, "output": 2.40}
    assert get_prices("qwen3.5")[0] == {"input": 0.60, "output": 3.60}
    # the generic keys still work for their own models
    assert get_prices("qwen3-32b")[0] == {"input": 0.60, "output": 2.40}

    assert get_prices("minimax-m2.7")[0] == {"input": 0.24, "output": 0.96}
    assert get_prices("minimax-m3")[0] == {"input": 0.30, "output": 1.20}


def test_unpriced_cloud_models_still_flag_fallback():
    """Models we could not find a rate for must keep reporting fallback=True
    rather than silently borrowing a neighbouring model's price."""
    for tag in ("glm-5.1:cloud", "gemma4:cloud", "nemotron-3-super:cloud"):
        assert get_prices(tag)[1] is True, f"{tag} should still be unpriced"
