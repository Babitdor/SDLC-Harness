"""Self-check for the filesystem task harness — no Docker required.

Covers the task loader and the dataset itself. The pipeline (run_pipeline)
needs Docker + model creds and is exercised separately.
"""

from __future__ import annotations

from pathlib import Path

from harness_eval.tasks.loader import load_suite, load_task

DATASET = Path(__file__).resolve().parents[1] / "dataset"


def test_loader_parses_task1():
    task = load_task(DATASET / "Task-1")
    assert task.project_id == "task1-warehouse"
    assert task.prompt.strip()
    assert {f for f, _ in task.source_files} == {"requirements.md", "morphological-box.md"}
    assert [g.name for g in task.graders] == ["cost-tokens", "process-metrics"]


def test_dataset_samples_are_measurable():
    """Every task must be a workload the cost/process graders can measure.

    A task with no source documents halts at ingestion and measures only
    orchestration overhead — the defect that made an earlier 20-trial cost
    batch report on a pipeline that produced nothing. Project ids become
    container names, so they must be unique and container-safe.
    """
    import re

    tasks = load_suite(DATASET)
    assert tasks, "dataset is empty"
    ids = [t.project_id for t in tasks]
    assert len(ids) == len(set(ids)), "duplicate project_id"
    for t in tasks:
        assert t.source_files, f"{t.id} ships no source documents"
        assert re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", t.project_id), t.project_id
        assert [g.name for g in t.graders] == ["cost-tokens", "process-metrics"], t.id
        assert not (t.path / "expected").exists(), f"{t.id} carries gold artefacts"
