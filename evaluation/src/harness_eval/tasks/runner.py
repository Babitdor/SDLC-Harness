"""Standalone task-suite runner: task x trials -> graders -> JSON report."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import statistics
import time
import uuid
from pathlib import Path
from typing import Any

from harness_eval.runner import _normalize_result, get_evaluator
from harness_eval.tasks.loader import GraderSpec, Task, load_suite

logger = logging.getLogger("harness_eval.tasks")

async def run_suite(
    suite_dir: str | Path,
    trials: int = 1,
    output: str | Path | None = None,
    only: str | None = None,
    keep_containers: bool = False,
) -> dict[str, Any]:
    """Run every task in a suite ``trials`` times and grade each trial.

    ``only`` restricts the run to a single task by folder name (e.g. "Task-1").
    """
    tasks = load_suite(Path(suite_dir))
    if only:
        tasks = [t for t in tasks if t.id.lower() == only.lower()]
        if not tasks:
            raise ValueError(f"No task named {only!r} under {suite_dir}")
    logger.info("Loaded %d task(s) from %s", len(tasks), suite_dir)

    report: dict[str, Any] = {"suite": str(suite_dir), "trials": trials, "tasks": []}
    for task in tasks:
        report["tasks"].append(await _run_task(task, trials, cleanup=not keep_containers))

    report["summary"] = _summarize(report["tasks"])

    out_path = Path(output) if output else Path(suite_dir).parent / "results" / f"report-{int(time.time())}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote report -> %s", out_path)
    report["report_path"] = str(out_path)
    return report


async def _run_task(task: Task, trials: int, cleanup: bool = False) -> dict[str, Any]:
    logger.info("=== %s (%d source file(s), %d grader(s)) ===",
                task.id, len(task.source_files), len(task.graders))
    trial_results: list[dict[str, Any]] = []
    for t in range(trials):
        trial_results.append(await _run_trial(task, t, cleanup=cleanup))

    # Aggregate each grader's score across trials.
    per_grader: dict[str, list[float]] = {}
    for tr in trial_results:
        for name, res in tr["graders"].items():
            score = res.get("score")
            if isinstance(score, (int, float)):
                per_grader.setdefault(name, []).append(float(score))

    return {
        "task": task.id,
        "project_id": task.project_id,
        "trials": trial_results,
        "mean_scores": {n: statistics.mean(v) for n, v in per_grader.items() if v},
    }


async def _run_trial(task: Task, trial: int, cleanup: bool = False) -> dict[str, Any]:
    # Import here so the loader/report paths work without the heavy backend.
    from harness_eval.run import run_pipeline

    thread_id = f"{task.project_id}-t{trial}-{uuid.uuid4().hex[:8]}"
    inputs = {
        "request": task.prompt,
        "source_files": task.source_files,
        "project_id": task.project_id,
        "thread_id": thread_id,
        "cleanup": cleanup,
    }
    t0 = time.time()
    outputs = await run_pipeline(inputs)
    elapsed = time.time() - t0

    graders: dict[str, Any] = {}
    for spec in task.graders:
        graders[spec.name] = await _grade(task, spec, inputs, outputs)

    return {
        "trial": trial,
        "thread_id": thread_id,
        "elapsed_s": round(elapsed, 1),
        "pipeline_error": outputs.get("_error"),
        "graders": graders,
    }


async def _grade(
    task: Task, spec: GraderSpec, inputs: dict, outputs: dict
) -> dict[str, Any]:
    factory = get_evaluator(spec.name)
    if factory is None:
        return {"error": f"unknown grader '{spec.name}'", "score": None}

    grader_fn = factory()  # registered entry is a factory returning the evaluator
    run_obj = {"outputs": outputs}
    example_obj = {"inputs": inputs, "outputs": {}}

    try:
        result = grader_fn(run_obj, example_obj)
        if inspect.isawaitable(result):
            result = await result
        return _normalize_result(result)
    except Exception as exc:  # a broken grader shouldn't kill the suite
        logger.exception("Grader %s failed on %s", spec.name, task.id)
        return {"error": str(exc), "score": None}


def _summarize(task_reports: list[dict]) -> dict[str, Any]:
    all_scores: list[float] = []
    for tr in task_reports:
        all_scores.extend(tr["mean_scores"].values())
    return {
        "tasks": len(task_reports),
        "overall_mean_score": round(statistics.mean(all_scores), 4) if all_scores else None,
    }
