"""Tests for the process-metrics measurement pipeline.

Covers reasoning-token extraction from every provider shape, the strict
invocation counter, the run_pipeline process summariser, and the evaluator's
budget-aware scoring. All deterministic — no Docker / model creds.
"""

from __future__ import annotations

import asyncio

from harness_eval.evaluators.process_metrics_eval import process_metrics_evaluator
from harness_eval.usage_capture import (
    UsageCaptureHandler,
    _extract_reasoning_tokens,
    _usage_from_llm_end,
)


# ── reasoning-token extraction ─────────────────────────────────────────────

def test_reasoning_from_openai_token_usage_details():
    tu = {
        "prompt_tokens": 100,
        "completion_tokens": 40,
        "completion_tokens_details": {"reasoning_tokens": 25},
    }
    usage = _usage_from_llm_end({"token_usage": tu}, None)
    assert usage["reasoning_tokens"] == 25
    assert usage["output_tokens"] == 40  # reasoning is a subset, not a replacement


def test_reasoning_from_anthropic_usage_shape():
    # ChatAnthropic reports llm_output["usage"] with output_tokens_details.
    lo = {"usage": {"input_tokens": 50, "output_tokens": 30,
                    "output_tokens_details": {"reasoning_tokens": 12}}}
    usage = _usage_from_llm_end(lo, None)
    assert usage["reasoning_tokens"] == 12
    assert usage["total_tokens"] == 80


def test_reasoning_from_langchain_usage_metadata():
    um = {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10,
          "output_token_details": {"reasoning": 2}}
    assert _extract_reasoning_tokens(None, um) == 2


def test_reasoning_absent_returns_zero():
    assert _extract_reasoning_tokens({"completion_tokens": 1}, None) == 0
    assert _extract_reasoning_tokens(None, {"input_tokens": 1}) == 0
    assert _extract_reasoning_tokens(None, None) == 0


# ── invocation counter ─────────────────────────────────────────────────────

def test_invocations_count_even_without_usage():
    handler = UsageCaptureHandler()
    # a call reporting usage…
    handler.on_llm_end(_FakeResponse(tu={"prompt_tokens": 100, "completion_tokens": 40}), **{})
    # …and one reporting none still counts as an invocation
    handler.on_llm_end(_FakeResponse(tu=None), **{})
    assert handler.invocations == 2
    assert len(handler.records) == 1
    summary = handler.summarize()
    assert summary["invocations"] == 2
    assert summary["calls"] == 1
    assert summary["reasoning_tokens"] == 0


def test_summary_includes_reasoning_total():
    handler = UsageCaptureHandler()
    handler.on_llm_end(
        _FakeResponse(tu={"prompt_tokens": 100, "completion_tokens": 40,
                          "completion_tokens_details": {"reasoning_tokens": 10}}),
        **{},
    )
    handler.on_llm_end(
        _FakeResponse(tu={"prompt_tokens": 50, "completion_tokens": 10,
                          "completion_tokens_details": {"reasoning_tokens": 4}}),
        **{},
    )
    assert handler.totals["reasoning_tokens"] == 14
    assert handler.summarize()["reasoning_tokens"] == 14


# ── run_pipeline process summariser ────────────────────────────────────────

def test_extract_process_summarises_call_order():
    from harness_eval.run import _extract_process

    outputs = {
        "agent_call_order": [
            {"name": "requirements-agent", "timestamp": 1.0},
            {"name": "functional-agent", "timestamp": 2.0},
            {"name": "requirements-agent", "timestamp": 3.0},
        ],
        "usage": {"invocations": 7, "calls": 7},
        "elapsed_s": 12.5,
    }
    _extract_process(outputs)
    proc = outputs["process"]
    assert proc["subagent_calls"] == {
        "requirements-agent": 2, "functional-agent": 1,
    }
    assert proc["agents_involved"] == ["functional-agent", "requirements-agent"]
    assert proc["llm_invocations"] == 7
    assert proc["elapsed_s"] == 12.5


def test_extract_process_empty_order():
    from harness_eval.run import _extract_process

    outputs = {"agent_call_order": [], "usage": {}, "elapsed_s": 0.0}
    _extract_process(outputs)
    assert outputs["process"]["subagent_calls"] == {}
    assert outputs["process"]["agents_involved"] == []
    assert outputs["process"]["llm_invocations"] == 0


# ── evaluator ──────────────────────────────────────────────────────────────

def _run(usage: dict, process: dict | None = None, elapsed_s: float = 1.0) -> dict:
    outputs = {"usage": usage, "elapsed_s": elapsed_s}
    if process is not None:
        outputs["process"] = process
    return {"outputs": outputs}


def test_process_metrics_evaluator_healthy():
    out = process_metrics_evaluator(
        _run(
            {"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500,
             "reasoning_tokens": 60, "calls": 4, "invocations": 5, "model": "o3"},
            {"subagent_calls": {"requirements-agent": 2, "layout-agent": 1},
             "agents_involved": ["layout-agent", "requirements-agent"],
             "llm_invocations": 5, "elapsed_s": 42.0},
            elapsed_s=42.0,
        ),
        {"inputs": {}},
    )
    assert out["score"] == 1.0, out
    assert out["extra"]["usage"]["reasoning_tokens"] == 60
    assert out["extra"]["process"]["subagent_calls"]["requirements-agent"] == 2
    assert out["extra"]["process"]["llm_invocations"] == 5
    assert "reasoning_tokens=60" in out["comment"]


def test_process_metrics_evaluator_over_invocation_budget():
    out = process_metrics_evaluator(
        _run(
            {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150,
             "invocations": 250, "calls": 250},
            {"subagent_calls": {"requirements-agent": 50},
             "agents_involved": ["requirements-agent"],
             "llm_invocations": 250, "elapsed_s": 100.0},
            elapsed_s=100.0,
        ),
        {"inputs": {"max_llm_invocations": 200}},
    )
    assert out["score"] == 0.0, out
    assert "PROCESS OVER BUDGET" in out["comment"]


def test_process_metrics_evaluator_no_usage_scores_healthy():
    out = process_metrics_evaluator(_run({}), {"inputs": {}})
    assert out["score"] == 1.0
    assert out["extra"]["usage"]["invocations"] == 0
    assert out["extra"]["process"]["subagent_calls"] == {}


def test_process_metrics_registered():
    from harness_eval.runner import get_evaluator, list_evaluators

    assert get_evaluator("process-metrics") is not None
    assert "process-metrics" in list_evaluators()


def test_process_metrics_dispatches_via_grade():
    """The filesystem task-suite grader dispatch resolves process-metrics."""
    from pathlib import Path

    from harness_eval.tasks.loader import GraderSpec, load_task
    from harness_eval.tasks.runner import _grade

    task = load_task(Path(__file__).resolve().parents[1] / "dataset" / "Task-25")
    spec = GraderSpec(name="process-metrics")
    outputs = {
        "usage": {"input_tokens": 500, "output_tokens": 50, "total_tokens": 550,
                  "reasoning_tokens": 20, "calls": 2, "invocations": 2, "model": "gpt-4o"},
        "process": {"subagent_calls": {"requirements-agent": 1, "layout-agent": 1},
                    "agents_involved": ["layout-agent", "requirements-agent"],
                    "llm_invocations": 2, "elapsed_s": 30.0},
        "elapsed_s": 30.0,
    }
    res = asyncio.run(_grade(task, spec, {"request": task.prompt}, outputs))
    assert isinstance(res.get("score"), (int, float)), res
    assert "llm_invocations" in (res.get("comment") or "")


class _FakeResponse:
    """Minimal stand-in for the langchain on_llm_end ``response``."""

    def __init__(self, tu):
        self.llm_output = {"token_usage": tu} if tu else None
        self.generations = None