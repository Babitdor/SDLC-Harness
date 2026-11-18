"""Run function for SDLC Harness evaluation.

Captures the full agent pipeline output for evaluation by LangSmith
evaluators. The run function is the bridge between the agent and the
evaluation framework — it invokes the orchestrator and collects all
artifacts, timestamps, and agent call order into a structured dict.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from harness_eval.usage_capture import UsageCaptureHandler, usage_from_messages

logger = logging.getLogger(__name__)

# Artifact extensions whose textual content is captured into
# ``artifact_contents`` for the evaluators. ``str.endswith`` accepts a tuple.
_TEXT_ARTIFACT_SUFFIXES = (".md", ".mmd", ".json", ".drawio", ".html", ".yaml", ".yml", ".feature")


def _coerce_requirements(inputs: dict[str, Any]) -> str:
    """Build the orchestrator's user message from a dataset example's inputs.

    Datasets carry different input schemas — ``pipeline-completeness`` uses
    ``requirements`` and ``dag-compliance`` uses ``request``. Accept either
    so a single target works across every dataset.

    When available, also includes the morphological box, knowledge base,
    and constraints to simulate a real user-provided input package.
    """
    # Start with the primary requirements text
    if inputs.get("requirements"):
        parts = [str(inputs["requirements"])]
    elif inputs.get("request"):
        parts = [str(inputs["request"])]
    else:
        parts = []
        for key in ("requirements_md", "bdd_md", "ibd_md"):
            if inputs.get(key):
                parts.append(f"## {key}\n{inputs[key]}")

    # Append supplementary inputs if present (real-world user input package)
    for key, heading in (
        ("box_md", "Morphological Box"),
        ("knowledge_base_md", "Knowledge Base & Standards"),
        ("constraints_md", "Constraints"),
    ):
        if inputs.get(key):
            parts.append(f"\n## {heading}\n{inputs[key]}")

    return "\n\n".join(parts)


async def run_pipeline(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run the full SDLC pipeline and capture outputs for evaluation.

    Designed to be passed to LangSmith's ``aevaluate()`` as the (async)
    target. LangSmith calls it with the example's ``inputs`` dict. It:

    1. Initialises the checkpointer and creates a Docker sandbox session
    2. Sends the derived requirements to the orchestrator (async)
    3. Collects produced artifacts, timestamps, contents, and agent order
    4. Returns a structured dict for evaluators

    Returns a dict with keys consumed by evaluators:
        - produced_artifacts: list of artifact paths
        - artifact_timestamps: {path: timestamp} for DAG compliance
        - artifact_contents: {path: content} for SysML validation
        - artifact_summary: concatenated summary for LLM-as-judge
        - agent_call_order: list of {name, timestamp} in call order
    """
    if not isinstance(inputs, dict):
        inputs = {}

    requirements = _coerce_requirements(inputs)
    # Unique thread per example so the per-thread Docker sandbox and
    # checkpoint state never collide across (possibly concurrent) examples.
    thread_id = str(inputs.get("thread_id") or f"eval-{uuid.uuid4().hex[:12]}")
    project_id = str(inputs.get("project_id") or "eval-project")

    outputs: dict[str, Any] = {
        "produced_artifacts": [],
        "artifact_timestamps": {},
        "artifact_contents": {},
        "artifact_summary": "",
        "agent_call_order": [],
        "process": {},
        "usage": {},
        "elapsed_s": 0.0,
    }

    if not requirements.strip():
        outputs["_error"] = "No usable requirements/request text in example inputs."
        return outputs

    backend = None
    try:
        from langchain_core.messages import HumanMessage

        from sdlc.services.agent import create_orchestrator, init_checkpointer

        # The orchestrator graph uses an async SQLite checkpointer that must
        # be initialised before create_orchestrator() — outside the FastAPI
        # lifespan we have to do it ourselves. Idempotent.
        await init_checkpointer()

        agent, backend = create_orchestrator(thread_id)

        # Simulated user uploads: seed the task's source files into the
        # project's sources/ dir the same way the real /upload endpoint does
        # (pre-create the workspace, then upload). This makes the agent work
        # in project_<project_id> and see the files as attachments.
        source_files = inputs.get("source_files") or []
        if source_files:
            from sdlc.services.file_upload import upload_file_to_container
            from sdlc.services.workspace import ProjectWorkspace

            ws = ProjectWorkspace(project_id, backend)
            ws.init_directories()
            for name, content in source_files:
                if isinstance(content, str):
                    content = content.encode("utf-8")
                await upload_file_to_container(
                    backend, thread_id, name, content, target_dir=ws.sources_dir
                )

        config = {
            "configurable": {"thread_id": thread_id},
            "metadata": {
                "project_id": project_id,
                "thread_id": thread_id,
                "eval_run": True,
            },
        }

        # Async invoke — the graph is compiled with an async checkpointer,
        # so the sync .invoke() path would raise. Attach a UsageCaptureHandler
        # so token usage from every model call (orchestrator + subagents) is
        # recorded for the cost/tokens evaluator.
        usage_handler = UsageCaptureHandler()
        config["callbacks"] = [usage_handler]

        t0 = time.time()
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=requirements)]},
            config=config,
        )
        outputs["elapsed_s"] = round(time.time() - t0, 2)

        _capture_usage(outputs, result, usage_handler)

        _collect_artifacts(backend, project_id, outputs)
        _extract_agent_order(result, outputs)
        _extract_process(outputs)
        _build_summary(outputs)

    except ImportError as exc:
        logger.warning("Agent dependencies not available: %s", exc)
        outputs["_error"] = f"Dependencies unavailable: {exc}"
    except Exception as exc:
        logger.exception("Pipeline run failed")
        outputs["_error"] = str(exc)
    finally:
        # Eval trials are throwaway — tear down the per-trial Docker container
        # unless the caller opts out. Off by default so the API/chat path (which
        # persists per-chat containers for workspace data) is unaffected.
        if inputs.get("cleanup") and backend is not None:
            try:
                backend.close(remove=True)
            except Exception:
                logger.warning("Container cleanup failed for %s", thread_id, exc_info=True)

    return outputs


def _capture_usage(
    outputs: dict[str, Any],
    result: Any,
    handler: UsageCaptureHandler,
) -> None:
    """Populate ``outputs["usage"]`` from the callback handler (preferred) or
    fall back to summing ``usage_metadata`` across the result messages.

    The handler captures every model call (orchestrator + subagents); the
    message fallback only sees the final chain, so it is a lower bound used
    only when the callback was not invoked by the provider.
    """
    summary = handler.summarize()
    totals = handler.totals
    have_callback_usage = bool(handler.records) or totals["total_tokens"] > 0

    if have_callback_usage:
        outputs["usage"] = summary
        return

    try:
        messages = result.get("messages", []) if isinstance(result, dict) else []
        msg_usage = usage_from_messages(messages)
    except Exception:
        msg_usage = {}
    if msg_usage.get("total_tokens"):
        outputs["usage"] = msg_usage
    else:
        outputs["usage"] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "reasoning_tokens": 0,
            "calls": 0,
            "invocations": 0,
            "model": None,
        }


def _discover_project_root(backend: Any, project_id: str) -> str | None:
    """Find the workspace ``project_*`` directory the pipeline actually used.

    The orchestrator names its own project folder from the requirements (e.g.
    ``/workspace/project_uav``) rather than the eval's ``project_id``, so we
    can't assume the path. Prefer the conventional ``project_<project_id>`` dir
    when it has content; otherwise pick whichever ``project_*`` directory holds
    the most files (the one the run populated).
    """
    preferred = f"/workspace/project_{project_id}"
    listing = backend.execute(
        "find /workspace -maxdepth 1 -type d -name 'project_*' 2>/dev/null"
    )
    if listing.exit_code != 0:
        return None
    candidates = [d.strip() for d in (listing.output or "").splitlines() if d.strip()]
    if not candidates:
        return None

    def _file_count(directory: str) -> int:
        res = backend.execute(
            f"find {directory} -type f -not -path '*/.*' 2>/dev/null | wc -l"
        )
        try:
            return int((res.output or "0").strip())
        except (ValueError, AttributeError):
            return 0

    if preferred in candidates and _file_count(preferred) > 0:
        return preferred
    return max(candidates, key=_file_count)


def _collect_artifacts(
    backend: Any,
    project_id: str,
    outputs: dict[str, Any],
) -> None:
    """Scan the sandbox workspace and collect all artifacts."""
    try:
        ws_root = _discover_project_root(backend, project_id)
        if ws_root is None:
            logger.warning(
                "No project_* directory found under /workspace — "
                "the pipeline produced no workspace artifacts."
            )
            return

        # List all files in the discovered project directory
        result = backend.execute(
            f"find {ws_root} -type f -not -path '*/.*' 2>/dev/null | sort"
        )
        if result.exit_code != 0:
            logger.warning("Failed to list workspace files under %s", ws_root)
            return

        files = [f.strip() for f in (result.output or "").splitlines() if f.strip()]

        for file_path in files:
            rel_path = file_path.replace(ws_root + "/", "")
            outputs["produced_artifacts"].append(rel_path)

            # Get file modification time
            ts_result = backend.execute(
                f"stat -c '%Y' {file_path} 2>/dev/null"
            )
            if ts_result.exit_code == 0 and ts_result.output.strip():
                try:
                    outputs["artifact_timestamps"][rel_path] = float(
                        ts_result.output.strip()
                    )
                except ValueError:
                    pass

            # Read text content for the artifact types evaluators inspect:
            #   .md             — markdown deliverables
            #   .mmd/.yaml/.feature — validated diagram, contract and test files
            #   .json/.drawio/.html — machine-readable and rendered deliverables
            if rel_path.endswith(_TEXT_ARTIFACT_SUFFIXES):
                content_result = backend.execute(
                    f"cat {file_path} 2>/dev/null"
                )
                if content_result.exit_code == 0:
                    outputs["artifact_contents"][rel_path] = (
                        content_result.output or ""
                    )

    except Exception as exc:
        logger.warning("Failed to collect artifacts: %s", exc)


def _extract_agent_order(
    result: Any,
    outputs: dict[str, Any],
) -> None:
    """Extract the subagent call order from the orchestrator result.

    Subagent dispatches surface as ``task`` tool calls. LangChain normalises
    these onto ``msg.tool_calls`` (already-parsed ``args``); only some raw
    provider responses put them under ``additional_kwargs["tool_calls"]``
    (JSON-string ``arguments``). Read the normalised attribute first and fall
    back to ``additional_kwargs`` so the order isn't silently lost.
    """
    try:
        messages = result.get("messages", []) if isinstance(result, dict) else []
        for msg in messages:
            for name, args in _iter_task_calls(msg):
                outputs["agent_call_order"].append({
                    "name": args.get("subagent_type", "unknown"),
                    "timestamp": time.time(),
                })
    except Exception as exc:
        logger.warning("Failed to extract agent order: %s", exc)


def _extract_process(outputs: dict[str, Any]) -> None:
    """Summarise the run's *process* from the captured call order + usage.

    The workflow a multi-agent pipeline followed matters as much as its output:
    this condenses ``agent_call_order`` (every ``task`` tool dispatch) into
    per-subagent call counts and the set of agents involved, and folds in the
    LLM-invocation total and wall time so a single ``process`` block describes
    *how* the result was produced.

    Writes ``outputs["process"]`` as a plain dict (serialisation-safe):
      - ``subagent_calls``: {subagent_type: call_count} in first-appearance order
      - ``agents_involved``: sorted list of distinct subagent types
      - ``llm_invocations``: total model calls (0 when usage missing)
      - ``elapsed_s``: echo of the run wall time
    """
    order = outputs.get("agent_call_order") or []
    per_agent: dict[str, int] = {}
    for entry in order:
        name = str((entry or {}).get("name") or "unknown")
        per_agent[name] = per_agent.get(name, 0) + 1

    usage = outputs.get("usage") or {}
    outputs["process"] = {
        "subagent_calls": per_agent,
        "agents_involved": sorted(per_agent.keys()),
        "llm_invocations": int(usage.get("invocations") or usage.get("calls") or 0),
        "elapsed_s": outputs.get("elapsed_s") or 0.0,
    }


def _iter_task_calls(msg: Any):
    """Yield ``(name, args)`` for every ``task`` tool call on a message.

    Handles both the normalised ``msg.tool_calls`` shape (dict ``args``) and
    the raw ``additional_kwargs["tool_calls"]`` shape (JSON-string
    ``function.arguments``).
    """
    import json

    normalized = getattr(msg, "tool_calls", None) or []
    emitted = False
    for tc in normalized:
        if isinstance(tc, dict) and tc.get("name") == "task":
            args = tc.get("args") or {}
            if isinstance(args, dict):
                emitted = True
                yield "task", args

    # LangChain mirrors the same call into both fields — only fall back to the
    # raw shape when the normalised list gave us nothing, to avoid double-count.
    if emitted:
        return
    kwargs = getattr(msg, "additional_kwargs", None) or {}
    for tc in kwargs.get("tool_calls", []) or []:
        fn = tc.get("function", {}) if isinstance(tc, dict) else {}
        if fn.get("name") == "task":
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(args, dict):
                yield "task", args


def _build_summary(outputs: dict[str, Any]) -> None:
    """Build a text summary of produced artifacts for LLM-as-judge."""
    parts: list[str] = []
    for path in outputs.get("produced_artifacts", []):
        content = outputs.get("artifact_contents", {}).get(path, "")
        preview = content[:500] if content else "(binary or empty)"
        parts.append(f"## {path}\n{preview}\n")

    outputs["artifact_summary"] = "\n".join(parts) if parts else "No artifacts produced."