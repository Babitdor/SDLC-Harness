"""Load ``Task-*`` folders into Task objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class GraderSpec:
    """One grader binding from graders.yaml."""

    name: str


@dataclass
class Task:
    """A single filesystem task (one problem)."""

    id: str
    path: Path
    prompt: str
    project_id: str
    source_files: list[tuple[str, bytes]]
    graders: list[GraderSpec]


def load_task(task_dir: Path) -> Task:
    """Parse one ``Task-*`` directory."""
    task_dir = Path(task_dir)
    cfg = _read_yaml(task_dir / "graders.yaml")

    prompt_file = task_dir / cfg.get("prompt", "task.md")
    if not prompt_file.is_file():
        raise FileNotFoundError(f"{task_dir.name}: missing prompt file {prompt_file.name}")
    prompt = prompt_file.read_text(encoding="utf-8")

    # project_id must be filesystem/container-safe; default derived from folder.
    project_id = str(cfg.get("project_id") or task_dir.name.lower().replace(" ", "-"))

    source_files: list[tuple[str, bytes]] = []
    source_dir = task_dir / "source"
    if source_dir.is_dir():
        source_files = [
            (p.name, p.read_bytes())
            for p in sorted(source_dir.iterdir())
            if p.is_file()
        ]

    graders = [
        GraderSpec(name=g["name"])
        for g in (cfg.get("graders") or [])
    ]
    if not graders:
        raise ValueError(f"{task_dir.name}: graders.yaml lists no graders")

    return Task(
        id=task_dir.name,
        path=task_dir,
        prompt=prompt,
        project_id=project_id,
        source_files=source_files,
        graders=graders,
    )


def load_suite(suite_dir: Path) -> list[Task]:
    """Load every ``Task-*`` directory under a suite, sorted by name."""
    suite_dir = Path(suite_dir)
    task_dirs = sorted(
        p for p in suite_dir.iterdir() if p.is_dir() and p.name.lower().startswith("task-")
    )
    return [load_task(d) for d in task_dirs]


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"{path.parent.name}: missing {path.name}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
