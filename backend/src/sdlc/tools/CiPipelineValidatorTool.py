"""GitHub Actions workflow validator.

@DevOps writes planning/ci/pipeline.yml; this tool parses it and checks the
keys GitHub actually requires, so a pipeline that would be rejected on push is
caught in the sandbox instead.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)


class CiPipelineValidatorTool(BaseTool):
    """Parse a GitHub Actions workflow and report every structural problem."""

    name: str = "ci_pipeline_validator_tool"
    description: str = (
        "Validate a GitHub Actions workflow file.\n"
        "Input: the complete YAML text of planning/ci/pipeline.yml.\n"
        "Output: PASS plus the job list, or FAIL plus each problem and where "
        "it sits.\n"
        "Use after every write to the pipeline file — this tool is the "
        "authoritative gate."
    )

    def _run(self, document: str) -> str:
        """Validate *document* and return a human-readable verdict."""
        try:
            doc: Any = yaml.safe_load(document)
        except yaml.YAMLError as exc:
            return f"FAIL — YAML does not parse: {exc}"

        if not isinstance(doc, dict):
            return "FAIL — the workflow is not a YAML mapping."

        problems: list[str] = []

        # PyYAML's YAML 1.1 resolver turns the bare key `on` into the boolean
        # True, so a correct workflow has True where a reader sees "on".
        if "on" not in doc and True not in doc:
            problems.append('missing top-level `on` trigger')

        jobs = doc.get("jobs")
        if not isinstance(jobs, dict) or not jobs:
            problems.append("missing or empty top-level `jobs` mapping")
            jobs = {}

        for job_id, job in jobs.items():
            if not isinstance(job, dict):
                problems.append(f"job {job_id!r} is not a mapping")
                continue
            if not job.get("runs-on"):
                problems.append(f"job {job_id!r} declares no `runs-on`")
            steps = job.get("steps")
            if not isinstance(steps, list) or not steps:
                problems.append(f"job {job_id!r} declares no `steps`")
                continue
            for idx, step in enumerate(steps, start=1):
                if not isinstance(step, dict):
                    problems.append(f"job {job_id!r} step {idx} is not a mapping")
                    continue
                has_uses = "uses" in step
                has_run = "run" in step
                if has_uses and has_run:
                    problems.append(
                        f"job {job_id!r} step {idx} sets both `uses` and `run`"
                    )
                elif not has_uses and not has_run:
                    problems.append(
                        f"job {job_id!r} step {idx} sets neither `uses` nor `run`"
                    )

        if problems:
            body = "\n".join(f"  - {p}" for p in problems)
            return f"FAIL — {len(problems)} problem(s):\n{body}"

        return f"PASS — valid GitHub Actions workflow, jobs: {sorted(jobs)}."

    async def _arun(self, document: str) -> str:
        """Async wrapper."""
        return self._run(document)

