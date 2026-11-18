"""Filesystem task-suite harness.

A task suite is a directory of ``Task-*`` folders. Each task simulates a real
user session: ``source/`` files are the user's uploads, ``task.md`` is the
prompt they type, ``expected/`` holds ground truth, and ``graders.yaml``
declares which of the registered evaluators score the run.

Unlike the LangSmith dataset harness, this runner is standalone: it drives
``run_pipeline`` directly, dispatches graders from the evaluator registry with
plain dicts, and writes a JSON report. See ``runner.py``.
"""

from __future__ import annotations
