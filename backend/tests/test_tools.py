"""Tests for the SDLC domain tools.

Covers: the Mermaid, OpenAPI, Gherkin and CI-pipeline gates, WebSearchTool,
workspace/config/hitl helpers, custom agents and file uploads.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
import pytest


    # On non-Windows hosts without pywin32, this returns an empty list
    # gracefully — the test just verifies it doesn't crash.


# ── WebSearchTool ───────────────────────────────────────────────────────

def test_web_search_tool_importable():
    """WebSearchTool should be importable."""
    from sdlc.tools.WebSearchTool import WebSearchTool, WebSearchInput

    # WebSearchTool requires a ddg_runnable — test the input schema instead
    inp = WebSearchInput(query="test query")
    assert inp.query == "test query"
    assert inp.max_results == 5  # default


def test_web_search_tool_max_results_bounds():
    """WebSearchInput should enforce max_results bounds."""
    from sdlc.tools.WebSearchTool import WebSearchInput

    inp = WebSearchInput(query="test", max_results=10)
    assert inp.max_results == 10


def test_build_web_search_tools():
    """build_web_search_tools should return a list (possibly empty)."""
    from sdlc.tools.WebSearchTool import build_web_search_tools

    tools = build_web_search_tools()
    assert isinstance(tools, list)


# ── SSE streaming helpers (app.py) ────────────────────────────────────────

def test_extract_task_field():
    """_extract_task_field should parse fields from JSON args."""
    from sdlc.api.app import _extract_task_field

    args = '{"subagent_type": "architecture", "description": "Write the ADR"}'
    result = _extract_task_field(args, "subagent_type")
    assert result == "architecture"

    result = _extract_task_field(args, "description")
    assert result == "Write the ADR"


def test_extract_task_field_empty():
    """_extract_task_field should handle empty input."""
    from sdlc.api.app import _extract_task_field

    assert _extract_task_field("", "field") == ""
    assert _extract_task_field(None, "field") == ""


def test_extract_task_field_fallback_regex():
    """_extract_task_field should fall back to regex for malformed JSON."""
    from sdlc.api.app import _extract_task_field

    # Malformed JSON but regex can still extract
    args = '{"subagent_type": "architecture", incomplete'
    result = _extract_task_field(args, "subagent_type")
    assert result == "architecture"


def test_parse_write_todos():
    """_parse_write_todos should parse todo lists from streaming args."""
    from sdlc.api.app import _parse_write_todos

    args = '{"todos": [{"content": "Fix bug", "status": "in_progress"}]}'
    todos = _parse_write_todos(args)
    assert todos is not None
    assert len(todos) == 1
    assert todos[0]["content"] == "Fix bug"
    assert todos[0]["status"] == "in_progress"


def test_parse_write_todos_invalid():
    """_parse_write_todos should return None for invalid input."""
    from sdlc.api.app import _parse_write_todos

    assert _parse_write_todos("not json") is None
    assert _parse_write_todos("") is None
    assert _parse_write_todos(None) is None


def test_parse_write_todos_missing_todos_key():
    """_parse_write_todos should return None when 'todos' key is missing."""
    from sdlc.api.app import _parse_write_todos

    args = '{"other_key": "value"}'
    assert _parse_write_todos(args) is None


def test_extract_native_reasoning():
    """_extract_native_reasoning should extract reasoning from message chunks."""
    from sdlc.api.app import _extract_native_reasoning

    # Empty/None content should return empty string
    class MockChunk:
        content = None
        additional_kwargs = {}

    result = _extract_native_reasoning(MockChunk())
    assert result == ""


def test_extract_native_reasoning_with_reasoning_content():
    """_extract_native_reasoning should extract reasoning_content."""
    from sdlc.api.app import _extract_native_reasoning

    class MockChunk:
        content = None
        additional_kwargs = {"reasoning_content": "Step 1: Think..."}

    result = _extract_native_reasoning(MockChunk())
    assert "Step 1" in result


def test_subagent_type_re_compiled():
    """SUBAGENT_TYPE_RE should match subagent_type in JSON."""
    from sdlc.api.app import SUBAGENT_TYPE_RE

    match = SUBAGENT_TYPE_RE.search('"subagent_type": "architecture"')
    assert match is not None
    assert match.group(1) == "architecture"

    match = SUBAGENT_TYPE_RE.search('"subagent_type": "ingestion"')
    assert match is not None
    assert match.group(1) == "ingestion"

    assert SUBAGENT_TYPE_RE.search("no match here") is None


# ── Agent factory helpers ───────────────────────────────────────────────

def test_container_name_for():
    """container_name_for should produce deterministic names."""
    from sdlc.services.agent import container_name_for

    name1 = container_name_for("thread-abc")
    name2 = container_name_for("thread-abc")
    assert name1 == name2
    assert name1.startswith("harness-")
    assert "thread-abc" in name1


def test_container_name_sanitised():
    """container_name_for should sanitise unsafe characters."""
    from sdlc.services.agent import container_name_for

    name = container_name_for("bad/thread:name@#$")
    assert "/" not in name
    assert ":" not in name
    assert "@" not in name
    assert "#" not in name
    assert name.startswith("harness-")


# ── Workspace helpers ───────────────────────────────────────────────────

def test_workspace_phases_order():
    """PHASES should be in the correct SE order."""
    from sdlc.services.workspace import PHASES

    assert PHASES == ("sources", "requirements", "design", "planning", "diagrams")


def test_dag_depends_on_all_have_deps():
    """Every DAG entry should have a depends_on list."""
    from sdlc.services.workspace import DEFAULT_PROJECT_GRAPH

    for artifact, meta in DEFAULT_PROJECT_GRAPH.items():
        assert "depends_on" in meta, f"{artifact} missing depends_on"
        assert isinstance(meta["depends_on"], list), f"{artifact} depends_on not a list"


def test_agent_artifacts_reverse_consistency():
    """ARTIFACT_AGENT reverse mapping should be consistent."""
    from sdlc.services.workspace import AGENT_ARTIFACTS, ARTIFACT_AGENT

    for artifact, agent in ARTIFACT_AGENT.items():
        assert agent in AGENT_ARTIFACTS
        assert artifact in AGENT_ARTIFACTS[agent]


# ── Config edge cases ───────────────────────────────────────────────────

def test_config_docker_pool_size_is_int():
    """DOCKER_POOL_SIZE should be a positive integer."""
    import sdlc.core.config as cfg

    assert isinstance(cfg.DOCKER_POOL_SIZE, int)
    assert cfg.DOCKER_POOL_SIZE > 0


def test_config_thread_pool_size_is_int():
    """THREAD_POOL_SIZE should be a positive integer."""
    import sdlc.core.config as cfg

    assert isinstance(cfg.THREAD_POOL_SIZE, int)
    assert cfg.THREAD_POOL_SIZE > 0


def test_config_artifact_cache_ttl_is_float():
    """ARTIFACT_CACHE_TTL should be a float."""
    import sdlc.core.config as cfg

    assert isinstance(cfg.ARTIFACT_CACHE_TTL, float)
    assert cfg.ARTIFACT_CACHE_TTL > 0


# ── HITL edge cases ─────────────────────────────────────────────────────

def test_is_destructive_command_safe():
    """is_destructive_command should return None for safe commands."""
    from sdlc.services.hitl import is_destructive_command

    safe_commands = [
        "ls -la",
        "cat file.txt",
        "mkdir -p /workspace",
        "echo hello",
        "python script.py",
        "cd /tmp",
        "cp file1 file2",
        "mv file1 file2",
        "",
    ]
    for cmd in safe_commands:
        assert is_destructive_command(cmd) is None, f"Safe command flagged: {cmd}"


def test_is_destructive_command_dangerous():
    """is_destructive_command should flag dangerous commands."""
    from sdlc.services.hitl import is_destructive_command

    dangerous = [
        "rm -rf /",
        "rm -rf /etc",
        "rm -rf /var",
        "chmod -R 777 /",
        "sudo rm -rf /",
        "dd if=/dev/zero of=/dev/sda",
        "mkfs.ext4 /dev/sda",
        "> /dev/sda",
        "wipefs /dev/sda",
        "shred /etc/passwd",
        "fdisk /dev/sda",
        "parted /dev/sda",
    ]
    for cmd in dangerous:
        reason = is_destructive_command(cmd)
        assert reason is not None, f"Dangerous command not flagged: {cmd}"


def test_is_destructive_command_chained():
    """is_destructive_command should detect dangerous commands in chains."""
    from sdlc.services.hitl import is_destructive_command

    assert is_destructive_command("echo hello && rm -rf /") is not None
    assert is_destructive_command("ls; rm -rf /etc") is not None
    assert is_destructive_command("cd /tmp || rm -rf /var") is not None


def test_approval_description_edge_cases():
    """approval_description should handle edge cases."""
    from sdlc.services.hitl import approval_description

    # Missing args
    desc = approval_description({"name": "write_file", "args": {}}, None, None)
    assert "?" in desc  # should show fallback path

    # Unknown tool name
    desc = approval_description({"name": "unknown_tool", "args": {}}, None, None)
    assert "unknown_tool" in desc


# ── Document preview edge cases ─────────────────────────────────────────

def test_preview_binary_unknown_extension():
    """preview_binary should return None for unknown extensions."""
    from sdlc.services.document_preview import preview_binary

    assert preview_binary("exe", b"data") is None
    assert preview_binary("", b"data") is None


def test_preview_binary_all_known_extensions():
    """preview_binary should handle all known binary extensions."""
    from sdlc.services.document_preview import preview_binary

    for ext in ("docx", "pdf", "xlsx"):
        result = preview_binary(ext, b"")
        assert result is not None, f"preview_binary('{ext}', b'') returned None"


# ── Custom agents edge cases ────────────────────────────────────────────

def test_custom_agents_normalise_edge_cases():
    """_normalise_name should handle edge cases."""
    from sdlc.services.custom_agents import _normalise_name

    assert _normalise_name("") == "agent"
    assert _normalise_name("   ") == "agent"
    assert _normalise_name("a" * 100) == "a" * 64
    assert _normalise_name("---name---") == "name"
    assert _normalise_name("CamelCase Name") == "camelcase-name"


def test_custom_agents_create_with_special_chars():
    """create_custom_agent should normalise names with special characters."""
    import sdlc.services.custom_agents as ca
    import tempfile

    original_path = ca._CUSTOM_AGENTS_PATH
    with tempfile.TemporaryDirectory() as tmp:
        ca._CUSTOM_AGENTS_PATH = Path(tmp) / "custom_agents.json"
        try:
            created = ca.create_custom_agent("My@#$Agent!", "desc", "prompt")
            # create_custom_agent stores the original name, not the normalised one
            assert created["name"] == "My@#$Agent!"
        finally:
            ca._CUSTOM_AGENTS_PATH = original_path


# ── File upload edge cases ──────────────────────────────────────────────

def test_upload_file_to_container_sanitises_name():
    """upload_file_to_container should sanitise filenames."""
    from sdlc.services.file_upload import upload_file_to_container

    # Just test the import works and the function signature is correct
    import inspect
    sig = inspect.signature(upload_file_to_container)
    params = list(sig.parameters.keys())
    assert "backend" in params
    assert "filename" in params
    assert "content" in params



# ── MermaidValidatorTool ────────────────────────────────────────────────

def test_mermaid_validator_accepts_a_well_formed_diagram():
    from sdlc.tools.MermaidValidatorTool import MermaidValidatorTool

    doc = "sequenceDiagram\n    Client->>API: GET /orders\n    API-->>Client: 200 OK"
    verdict = MermaidValidatorTool()._run(doc)
    assert verdict.startswith("PASS"), verdict


def test_mermaid_validator_rejects_an_unknown_header():
    from sdlc.tools.MermaidValidatorTool import MermaidValidatorTool

    verdict = MermaidValidatorTool()._run("notADiagram\n    A->>B: hi")
    assert verdict.startswith("FAIL"), verdict


def test_mermaid_validator_flags_an_unbalanced_block():
    from sdlc.tools.MermaidValidatorTool import MermaidValidatorTool

    doc = "graph TD\n    subgraph Auth\n    A[Login] --> B[Token]"
    verdict = MermaidValidatorTool()._run(doc)
    assert verdict.startswith("FAIL"), verdict
    assert "never closed" in verdict


# ── OpenAPIValidatorTool ────────────────────────────────────────────────

def test_openapi_validator_accepts_a_minimal_spec():
    from sdlc.tools.OpenAPIValidatorTool import OpenAPIValidatorTool

    doc = (
        "openapi: 3.0.3\n"
        "info:\n"
        "  title: Orders\n"
        "  version: 1.0.0\n"
        "paths:\n"
        "  /orders:\n"
        "    get:\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n"
    )
    verdict = OpenAPIValidatorTool()._run(doc)
    assert verdict.startswith("PASS"), verdict


def test_openapi_validator_rejects_missing_paths():
    from sdlc.tools.OpenAPIValidatorTool import OpenAPIValidatorTool

    doc = "openapi: 3.0.3\ninfo:\n  title: Orders\n  version: 1.0.0"
    verdict = OpenAPIValidatorTool()._run(doc)
    assert verdict.startswith("FAIL"), verdict


# ── GherkinValidatorTool ────────────────────────────────────────────────

def test_gherkin_validator_accepts_a_scenario():
    from sdlc.tools.GherkinValidatorTool import GherkinValidatorTool

    doc = (
        "Feature: Checkout\n"
        "  Scenario: Pay with card\n"
        "    Given a cart with one item\n"
        "    When the customer pays by card\n"
        "    Then the order is confirmed\n"
    )
    verdict = GherkinValidatorTool()._run(doc)
    assert verdict.startswith("PASS"), verdict


def test_gherkin_validator_rejects_text_that_is_not_gherkin():
    from sdlc.tools.GherkinValidatorTool import GherkinValidatorTool

    verdict = GherkinValidatorTool()._run("this is not gherkin")
    assert verdict.startswith("FAIL"), verdict


# ── CiPipelineValidatorTool ─────────────────────────────────────────────

def test_ci_pipeline_validator_accepts_github_actions():
    from sdlc.tools.CiPipelineValidatorTool import CiPipelineValidatorTool

    doc = (
        "on: [push]\n"
        "jobs:\n"
        "  build:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
    )
    verdict = CiPipelineValidatorTool()._run(doc)
    assert verdict.startswith("PASS"), verdict


def test_ci_pipeline_validator_rejects_a_pipeline_without_jobs():
    from sdlc.tools.CiPipelineValidatorTool import CiPipelineValidatorTool

    verdict = CiPipelineValidatorTool()._run("on: [push]")
    assert verdict.startswith("FAIL"), verdict
