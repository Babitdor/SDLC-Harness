"""Pipeline and registry contract tests for the evaluation framework.

The harness evaluation measures cost and process only. These tests cover the
pipeline code that feeds those two graders (artifact collection, agent-order
extraction, requirement coercion) and the evaluator registry. They run without
an agent, Docker or network.
"""

from __future__ import annotations

from harness_eval.run import _coerce_requirements, _extract_agent_order
from harness_eval.runner import list_evaluators


# ── Registry ──────────────────────────────────────────────────────────────


def test_registry_is_measurement_only():
    """The harness is evaluated on cost and process alone.

    Artefact-quality graders were removed deliberately. If one reappears in the
    registry, this fails — scope creep has to be an explicit decision.
    """
    assert list_evaluators() == ["cost-tokens", "process-metrics"]


# ── Pipeline ──────────────────────────────────────────────────────────────


def test_coerce_requirements_handles_each_dataset_schema():
    assert _coerce_requirements({"requirements": "R"}) == "R"
    assert _coerce_requirements({"request": "do X"}) == "do X"
    combined = _coerce_requirements({"bdd_md": "B", "ibd_md": "I"})
    assert "B" in combined and "I" in combined
    assert _coerce_requirements({}) == ""


def _msg(*, tool_calls=None, additional_kwargs=None):
    from types import SimpleNamespace

    return SimpleNamespace(
        tool_calls=tool_calls, additional_kwargs=additional_kwargs
    )


def test_extract_agent_order_reads_normalized_tool_calls():
    """LangChain puts parsed subagent dispatches on ``msg.tool_calls`` —
    the previous code only read ``additional_kwargs`` and lost them."""
    out = {"agent_call_order": []}
    result = {"messages": [
        _msg(tool_calls=[{"name": "task", "args": {"subagent_type": "requirements"}}]),
        _msg(tool_calls=[{"name": "task", "args": {"subagent_type": "functional"}}]),
    ]}
    _extract_agent_order(result, out)
    assert [a["name"] for a in out["agent_call_order"]] == ["requirements", "functional"]


def test_extract_agent_order_falls_back_to_additional_kwargs():
    out = {"agent_call_order": []}
    result = {"messages": [_msg(additional_kwargs={"tool_calls": [
        {"function": {"name": "task", "arguments": '{"subagent_type": "ingestion"}'}}
    ]})]}
    _extract_agent_order(result, out)
    assert [a["name"] for a in out["agent_call_order"]] == ["ingestion"]


def test_extract_agent_order_no_double_count_when_mirrored():
    """A message carrying the same call in both fields must count it once."""
    out = {"agent_call_order": []}
    result = {"messages": [_msg(
        tool_calls=[{"name": "task", "args": {"subagent_type": "logical"}}],
        additional_kwargs={"tool_calls": [
            {"function": {"name": "task", "arguments": '{"subagent_type": "logical"}'}}
        ]},
    )]}
    _extract_agent_order(result, out)
    assert [a["name"] for a in out["agent_call_order"]] == ["logical"]


def test_collect_artifacts_captures_layout_filetypes():
    """run_pipeline must capture every text artifact type, not just .md —
    otherwise content-based graders never receive their input."""
    from harness_eval.run import _TEXT_ARTIFACT_SUFFIXES

    for suffix in (".md", ".mmd", ".json", ".drawio", ".html", ".yaml", ".feature"):
        assert suffix in _TEXT_ARTIFACT_SUFFIXES


class _FakeExec:
    def __init__(self, output="", exit_code=0):
        self.output = output
        self.exit_code = exit_code


class _FakeSandbox:
    """Minimal sandbox backend that answers the shell commands
    ``_collect_artifacts`` issues, backed by an in-memory file map."""

    def __init__(self, files: dict):
        self.files = files

    def execute(self, cmd: str):
        if "maxdepth 1 -type d -name 'project_*'" in cmd:
            dirs = sorted(
                {"/".join(p.split("/")[:3]) for p in self.files
                 if p.startswith("/workspace/project_")}
            )
            return _FakeExec("\n".join(dirs))
        if "find" in cmd and "-type f" in cmd:
            ws = cmd.split("find ")[1].split(" -type")[0].strip()
            matching = sorted(p for p in self.files if p.startswith(ws))
            return _FakeExec("\n".join(matching))
        if "stat" in cmd:
            return _FakeExec("0")
        if "cat " in cmd:
            path = cmd.split("cat ")[1].split(" 2>/dev/null")[0].strip()
            return _FakeExec(self.files.get(path, ""))
        return _FakeExec("")


def test_collect_artifacts_discovers_actual_project_dir():
    """The orchestrator names its own project_<x> folder from the requirements,
    so collection must discover it — not assume project_<eval_project_id>."""
    from harness_eval.run import _collect_artifacts

    files = {
        "/workspace/project_uav/requirements/REQUIREMENTS.md": "REQ-001: foo",
        "/workspace/project_uav/diagrams/class.mmd": "classDiagram",
        "/workspace/project_uav/index.md": "# index",
    }
    out = {"produced_artifacts": [], "artifact_timestamps": {}, "artifact_contents": {}}
    # Pass a project_id that does NOT match the real dir.
    _collect_artifacts(_FakeSandbox(files), "eval-project", out)

    assert "requirements/REQUIREMENTS.md" in out["produced_artifacts"]
    assert "diagrams/class.mmd" in out["produced_artifacts"]
    assert out["artifact_contents"]["diagrams/class.mmd"].startswith("classDiagram")


def test_normalize_result_folds_unknown_keys_into_extra():
    from harness_eval.runner import _normalize_result

    out = _normalize_result(
        {"score": 0.5, "comment": "c", "dimension_scores": {"a": 1}, "metrics": {"b": 2}}
    )
    assert set(out) <= {"key", "score", "value", "comment", "correction",
                        "evaluator_info", "feedback_config", "source_run_id",
                        "target_run_id", "extra"}
    assert out["extra"]["dimension_scores"] == {"a": 1}
    assert out["extra"]["metrics"] == {"b": 2}
    # Standard-only results pass through untouched.
    assert _normalize_result({"score": 1, "comment": "ok"}) == {"score": 1, "comment": "ok"}


def test_standardize_evaluator_preserves_name_and_normalizes():
    import asyncio

    from harness_eval.runner import _standardize_evaluator

    def sync_eval(run, example):
        return {"score": 1, "weird_key": 7}

    async def async_eval(run, example):
        return {"score": 0, "another_weird": 9}

    w_sync = _standardize_evaluator(sync_eval)
    assert w_sync.__name__ == "sync_eval"
    assert w_sync(None, None)["extra"] == {"weird_key": 7}

    w_async = _standardize_evaluator(async_eval)
    assert w_async.__name__ == "async_eval"
    assert asyncio.run(w_async(None, None))["extra"] == {"another_weird": 9}
