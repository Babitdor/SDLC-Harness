"""CLI: run a filesystem task suite.

    uv run python -m harness_eval.tasks run --task Task-23 --trials 3
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

# The single evaluation dataset: evaluation/dataset/Task-*.
DATASET_DIR = Path(__file__).resolve().parents[3] / "dataset"

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="SDLC filesystem task-suite runner")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run a task suite")
    run_p.add_argument("--suite", default=str(DATASET_DIR), help="Suite directory (default: evaluation/dataset)")
    run_p.add_argument("--task", default=None, help="Run only this task by folder name (e.g. Task-1)")
    run_p.add_argument("--trials", type=int, default=1, help="Trials per task (default: 1)")
    run_p.add_argument("--output", default=None, help="Report path (default: evaluation/results/report-*.json)")
    run_p.add_argument("--keep-containers", action="store_true", help="Do not remove per-trial Docker containers after each run")

    args = parser.parse_args()
    if args.command != "run":
        parser.print_help()
        return

    from harness_eval.tasks.runner import run_suite

    report = asyncio.run(run_suite(
        args.suite, trials=args.trials, output=args.output, only=args.task,
        keep_containers=args.keep_containers,
    ))
    summary = report.get("summary", {})
    print(f"\nTasks: {summary.get('tasks')}  overall mean score: {summary.get('overall_mean_score')}")
    print(f"Report: {report.get('report_path')}")


if __name__ == "__main__":
    main()
