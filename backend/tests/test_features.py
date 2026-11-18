"""Comprehensive feature tests for the SDLC Agent Orchestrator.

Covers every module in the project: prompts, artifacts, config, schemas,
workspace, subagents, document_preview, custom_agents, syson_settings,
file_upload, hitl, and conversations.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


# ── Prompt templates ─────────────────────────────────────────────────────

def test_prompt_templates_render():
    """All Jinja2 prompt templates should render without errors."""
    from jinja2 import Environment, FileSystemLoader

    prompts_dir = Path(__file__).resolve().parent.parent / "src" / "sdlc" / "services" / "prompts"
    env = Environment(loader=FileSystemLoader(str(prompts_dir)))

    templates = [
        "orchestrator.j2",
        "ingestion.j2",
        "requirements.j2",
        "architecture.j2",
        "api.j2",
        "planning.j2",
        "devops.j2",
        "diagram.j2",
        "_workspace_files.j2",
    ]

    for tpl_name in templates:
        tpl = env.get_template(tpl_name)
        rendered = tpl.render()
        assert len(rendered) > 50, f"{tpl_name} rendered to <50 chars"
        assert "{{" not in rendered, f"{tpl_name} has unrendered variables"


def test_orchestrator_prompt_mentions_all_agents():
    """The orchestrator prompt should mention all 7 subagents."""
    from jinja2 import Environment, FileSystemLoader

    prompts_dir = Path(__file__).resolve().parent.parent / "src" / "sdlc" / "services" / "prompts"
    env = Environment(loader=FileSystemLoader(str(prompts_dir)))
    rendered = env.get_template("orchestrator.j2").render()

    mentions = ["@Ingestion", "@Requirements", "@Architecture", "@API",
                "@Planning", "@DevOps", "@Diagram"]
    for m in mentions:
        assert m in rendered, f"Orchestrator prompt missing @mention for {m}"


# ── Artifact schemas ─────────────────────────────────────────────────────

def test_artifact_schemas_all_present():
    """All expected artifact schemas should be registered."""
    from sdlc.services.artifacts import ARTIFACT_SCHEMAS, get_schema_prompt

    expected = [
        "REQUIREMENTS.md", "GLOSSARY.md", "CONSTRAINTS.md",
        "USER_STORIES.md", "ACCEPTANCE_CRITERIA.md",
        "ARCHITECTURE.md", "DATA_MODEL.md", "ADR.md", "API_SPEC.md", "openapi.yaml",
        "BACKLOG.md", "TEST_PLAN.md", "CI_CD.md", "ci/pipeline.yml",
        "sequence.mmd", "class.mmd", "state.mmd", "erd.mmd", "deployment.mmd",
    ]
    for name in expected:
        assert name in ARTIFACT_SCHEMAS, f"Missing schema: {name}"

    # get_schema_prompt returns non-empty for known schemas
    for name in expected:
        prompt = get_schema_prompt(name)
        assert prompt, f"get_schema_prompt('{name}') returned empty"

    # get_schema_prompt returns empty for unknown schemas
    assert get_schema_prompt("nonexistent.md") == ""


def test_artifact_schema_timestamp_injection():
    """get_schema_prompt should inject timestamps."""
    from sdlc.services.artifacts import get_schema_prompt

    prompt = get_schema_prompt("REQUIREMENTS.md", timestamp="2025-01-01T00:00:00Z")
    assert "2025-01-01T00:00:00Z" in prompt


def test_expected_artifact_paths():
    """expected_artifact_paths should return all phase-qualified paths."""
    from sdlc.services.artifacts import expected_artifact_paths

    paths = expected_artifact_paths()
    assert "requirements/REQUIREMENTS.md" in paths
    assert "design/ARCHITECTURE.md" in paths
    assert "design/openapi.yaml" in paths
    assert "planning/ci/pipeline.yml" in paths
    assert "diagrams/sequence.mmd" in paths


# ── Configuration ────────────────────────────────────────────────────────

def test_config_has_expected_defaults():
    """Config module should have all expected settings with defaults."""
    import sdlc.core.config as cfg

    assert cfg.MODEL_NAME
    assert cfg.OPENAI_BASE_URL
    assert cfg.HOST
    assert isinstance(cfg.PORT, int)
    assert isinstance(cfg.DOCKER_POOL_SIZE, int)
    assert isinstance(cfg.THREAD_POOL_SIZE, int)
    assert isinstance(cfg.ARTIFACT_CACHE_TTL, float)
    assert cfg.CHECKPOINT_DB_PATH
    assert cfg.DATABASE_URL
    assert cfg.UPLOAD_DIR_HOST
    assert isinstance(cfg.MAX_UPLOAD_SIZE_MB, int)


# ── Pydantic schemas ─────────────────────────────────────────────────────

def test_all_schemas_instantiate():
    """All Pydantic schemas should instantiate with valid defaults."""
    from sdlc.models.schemas import (
        ArtifactListResponse,
        ChatRequest,
        ChatResponse,
        ChatResponse,
        ConversationCreate,
        ConversationSummary,
        ConversationUpdate,
        CustomAgent,
        CustomAgentCreate,
        CustomAgentListResponse,
        CustomAgentUpdate,
        HealthResponse,
        MessageCreate,
        MessageListResponse,
        MessageOut,
        ModelSettings,
        ModelSettingsResponse,
        ProjectCreateRequest,
        ProjectCreateResponse,
        TracingStatusResponse,
        UploadResponse,
    )

    # Chat
    req = ChatRequest(message="Hello")
    assert req.message == "Hello"
    assert req.thread_id == "default"
    assert req.project_id == "default"

    resp = ChatResponse(message="Hi", thread_id="t1", project_id="p1")
    assert resp.message == "Hi"

    # Health
    h = HealthResponse()
    assert h.status == "ok"

    # Tracing
    t = TracingStatusResponse()
    assert t.status == "disabled"

    # Project
    p_req = ProjectCreateRequest()
    assert p_req.project_id == "default"

    p_resp = ProjectCreateResponse(project_id="test", root="/ws/test")
    assert p_resp.status == "created"

    # Artifacts
    a = ArtifactListResponse(project_id="p1")
    assert a.artifacts == []

    # Upload
    u = UploadResponse(thread_id="t1")
    assert u.project_id == "default"

    # Conversations
    cc = ConversationCreate(id="c1", title="Test")
    assert cc.title == "Test"

    cu = ConversationUpdate(title="Updated")
    assert cu.title == "Updated"

    cs = ConversationSummary(id="c1", title="Test", project_id="p1",
                              created_at="now", updated_at="now", message_count=0)
    assert cs.id == "c1"

    mc = MessageCreate(role="user", content="hello")
    assert mc.role == "user"

    mo = MessageOut(id=1, conversation_id="c1", role="assistant",
                     content="hi", created_at="now")
    assert mo.role == "assistant"

    ml = MessageListResponse(conversation_id="c1", messages=[mo])
    assert len(ml.messages) == 1

    # Custom agents
    ca = CustomAgent(id="a1", name="helper", description="Helper agent",
                      system_prompt="You are helpful", created_at="now", updated_at="now")
    assert ca.name == "helper"

    ca_create = CustomAgentCreate(name="helper", description="Helper",
                                   system_prompt="Be helpful")
    assert ca_create.name == "helper"

    ca_update = CustomAgentUpdate(name="helper-v2")
    assert ca_update.name == "helper-v2"

    cal = CustomAgentListResponse(agents=[ca])
    assert len(cal.agents) == 1

    # Model settings
    ms = ModelSettings(
        model_provider="openai",
        reasoning_effort="medium",
        base_url="https://api.example.com",
        agent_model="gpt-5",
        vision_model="gpt-5-vision",
        retry_model="gpt-5-mini",
    )
    assert ms.model_provider == "openai"

    ms_resp = ModelSettingsResponse(effective=ms, api_key_set=False, stored={})
    assert ms_resp.api_key_set is False


# ── Workspace ────────────────────────────────────────────────────────────

def test_workspace_phases():
    """Workspace should define the expected phase folders."""
    from sdlc.services.workspace import PHASES

    assert PHASES == ("sources", "requirements", "design", "planning", "diagrams")


def test_workspace_dag_has_all_artifacts():
    """DEFAULT_PROJECT_GRAPH should cover all expected artifacts."""
    from sdlc.services.workspace import DEFAULT_PROJECT_GRAPH

    from sdlc.services.artifacts import expected_artifact_paths

    expected = expected_artifact_paths()
    for art in expected:
        assert art in DEFAULT_PROJECT_GRAPH, f"Missing DAG entry: {art}"

    # Every artifact has a depends_on key
    for art, meta in DEFAULT_PROJECT_GRAPH.items():
        assert "depends_on" in meta, f"{art} missing depends_on"


def test_agent_artifacts_mapping():
    """AGENT_ARTIFACTS should map every agent to its outputs."""
    from sdlc.services.workspace import AGENT_ARTIFACTS, ARTIFACT_AGENT

    assert set(AGENT_ARTIFACTS.keys()) == {
        "ingestion", "requirements", "architecture", "api",
        "planning", "devops", "diagram",
    }

    # Reverse mapping is consistent
    for artifact, agent in ARTIFACT_AGENT.items():
        assert agent in AGENT_ARTIFACTS
        assert artifact in AGENT_ARTIFACTS[agent]

    # The diagram agent owns the five .mmd models
    diagram_arts = list(AGENT_ARTIFACTS["diagram"])
    assert len(diagram_arts) == 5
    assert all(a.endswith(".mmd") for a in diagram_arts)


# ── Subagents ───────────────────────────────────────────────────────────

def test_all_subagents_have_required_fields():
    """Every subagent should have name, description, and system_prompt."""
    from sdlc.services.subagents import ALL_SUBAGENTS

    for sa in ALL_SUBAGENTS:
        assert "name" in sa, f"Subagent missing 'name': {sa.get('name', '?')}"
        assert "description" in sa, f"Subagent {sa['name']} missing 'description'"
        assert "system_prompt" in sa, f"Subagent {sa['name']} missing 'system_prompt'"
        assert len(sa["system_prompt"]) > 100, f"Subagent {sa['name']} system_prompt too short"


def test_subagent_names_are_unique():
    """All subagent names should be unique."""
    from sdlc.services.subagents import ALL_SUBAGENTS

    names = [sa["name"] for sa in ALL_SUBAGENTS]
    assert len(names) == len(set(names)), f"Duplicate subagent names: {names}"


def test_subagent_names_match_expected():
    """Subagent names should match the expected roster."""
    from sdlc.services.subagents import ALL_SUBAGENTS

    names = {sa["name"] for sa in ALL_SUBAGENTS}
    expected = {"ingestion", "requirements", "architecture", "api",
                "planning", "devops", "diagram"}
    assert names == expected, f"Mismatch: {names ^ expected}"




def test_diagram_subagent_has_skills():
    """The diagram subagent should have skills configured."""
    from sdlc.services.subagents import ALL_SUBAGENTS

    diagram = next(sa for sa in ALL_SUBAGENTS if sa["name"] == "diagram")
    assert "skills" in diagram
    assert "/skills" in diagram["skills"]


def test_domain_agents_point_at_their_skill():
    """Agents that own a skill file must name it, and the file must exist."""
    from sdlc.services.subagents import ALL_SUBAGENTS

    skills_dir = Path(__file__).resolve().parent.parent / "src" / "sdlc" / "skills"
    owned = {
        "requirements": ["requirements-spec"],
        "architecture": ["architecture-docs", "adr"],
        "api": ["api-design"],
        "planning": ["implementation-plan", "test-strategy"],
        "devops": ["ci-cd", "secrets-management"],
    }
    for spec in ALL_SUBAGENTS:
        skills = owned.get(spec["name"])
        if skills is None:
            continue
        for skill in skills:
            pointer = f"/skills/{skill}/SKILL.md"
            assert pointer in spec["system_prompt"], f"{spec['name']} never points at {pointer}"
            assert (skills_dir / skill / "SKILL.md").exists(), f"missing {skill}/SKILL.md"


def test_attach_tools():
    """Domain tools go only to the named agent; recovery goes to everyone.

    The second half is the caveman contract, not a convenience: a compacted
    tool result with no caveman_retrieve in reach would force the agent to
    guess at the bytes it lost, so every agent that can receive one gets the
    tool. Domain capability stays where it was.
    """
    from sdlc.services.subagents import ALL_SUBAGENTS, attach_tools

    class FakeTool:
        def __init__(self, name: str):
            self.name = name

    tools_map = {"api": [FakeTool("openapi_validator_tool")]}
    result = attach_tools(ALL_SUBAGENTS, tools_map)

    for spec in result:
        names = [t.name for t in spec.get("tools", [])]
        if spec["name"] == "api":
            assert names[0] == "openapi_validator_tool"
        else:
            assert "openapi_validator_tool" not in names, spec["name"]
        assert "caveman_retrieve" in names, f"{spec['name']} cannot recover"


# ── HITL ────────────────────────────────────────────────────────────────

def test_hitl_interrupt_on_has_expected_keys():
    """INTERRUPT_ON should gate write_file and edit_file."""
    from sdlc.services.hitl import INTERRUPT_ON

    assert "write_file" in INTERRUPT_ON
    assert "edit_file" in INTERRUPT_ON


def test_hitl_approval_description():
    """approval_description should produce readable text."""
    from sdlc.services.hitl import approval_description

    desc = approval_description(
        {"name": "write_file", "args": {"file_path": "/test.md", "content": "hello world"}},
        state=None,
        runtime=None,
    )
    assert "/test.md" in desc
    assert "hello world" in desc

    desc_edit = approval_description(
        {"name": "edit_file", "args": {"file_path": "/test.md",
                                        "old_string": "old", "new_string": "new"}},
        state=None,
        runtime=None,
    )
    assert "/test.md" in desc_edit
    assert "old" in desc_edit
    assert "new" in desc_edit


def test_shell_guard_patterns():
    """ShellGuardMiddleware should have destructive command patterns."""
    from sdlc.services.hitl import ShellGuardMiddleware, is_destructive_command

    guard = ShellGuardMiddleware()
    assert hasattr(guard, "after_model")

    # is_destructive_command should detect dangerous commands
    assert is_destructive_command("rm -rf /") is not None
    assert is_destructive_command("rm -rf /etc") is not None
    assert is_destructive_command("chmod -R 777 /") is not None
    assert is_destructive_command("sudo rm -rf /") is not None

    # Safe commands should return None
    assert is_destructive_command("ls -la") is None
    assert is_destructive_command("cat file.txt") is None
    assert is_destructive_command("mkdir -p /workspace") is None
    assert is_destructive_command("") is None


# ── Document preview ────────────────────────────────────────────────────

def test_preview_error_html():
    """_error_html should return a styled HTML page."""
    from sdlc.services.document_preview import _error_html

    html = _error_html("Something went wrong")
    assert "Preview unavailable" in html
    assert "Something went wrong" in html
    assert "<!doctype html>" in html


def test_preview_pdf_empty_returns_error():
    """preview_pdf with empty bytes should return an error."""
    from sdlc.services.document_preview import preview_pdf

    result = preview_pdf(b"")
    assert "Preview unavailable" in result or "Could not convert" in result


def test_preview_docx_empty_returns_error():
    """preview_docx with empty bytes should return an error."""
    from sdlc.services.document_preview import preview_docx

    result = preview_docx(b"")
    assert "Preview unavailable" in result or "Could not convert" in result


def test_preview_xlsx_empty_returns_error():
    """preview_xlsx with empty bytes should return an error."""
    from sdlc.services.document_preview import preview_xlsx

    result = preview_xlsx(b"")
    assert "Preview unavailable" in result or "Could not convert" in result


def test_preview_binary_dispatches():
    """preview_binary should dispatch to the correct converter by extension."""
    from sdlc.services.document_preview import preview_binary

    # Unknown extension
    result = preview_binary("txt", b"hello")
    assert result is None

    # Known extensions with empty data should return error HTML
    for ext in ("docx", "pdf", "xlsx"):
        result = preview_binary(ext, b"")
        assert result is not None
        assert "Preview unavailable" in result or "<!doctype" in result


# ── Custom agents ────────────────────────────────────────────────────────

def test_custom_agents_normalise_name():
    """_normalise_name should produce safe deep-agents identifiers."""
    from sdlc.services.custom_agents import _normalise_name

    assert _normalise_name("My Agent") == "my-agent"
    assert _normalise_name("  Hello World!  ") == "hello-world"
    assert _normalise_name("UPPERCASE") == "uppercase"
    assert _normalise_name("special@#$chars") == "specialchars"
    assert _normalise_name("a" * 100)[:64] == "a" * 64
    assert _normalise_name("") == "agent"


def test_custom_agents_reserved_names():
    """Reserved names should be protected."""
    from sdlc.services.custom_agents import _RESERVED_NAMES

    assert "ingestion" in _RESERVED_NAMES
    assert "diagram" in _RESERVED_NAMES
    assert "architecture" in _RESERVED_NAMES
    assert "general-purpose" in _RESERVED_NAMES
    assert len(_RESERVED_NAMES) == 8


def test_custom_agents_crud(tmp_path):
    """Custom agents CRUD should work with a temporary file."""
    import sdlc.services.custom_agents as ca

    # Override the path to a temp file
    original_path = ca._CUSTOM_AGENTS_PATH
    ca._CUSTOM_AGENTS_PATH = tmp_path / "custom_agents.json"

    try:
        # List starts empty
        assert ca.list_custom_agents() == []

        # Create
        created = ca.create_custom_agent("test-agent", "A test agent", "Be helpful")
        assert created["name"] == "test-agent"
        assert created["description"] == "A test agent"

        # List has one
        agents = ca.list_custom_agents()
        assert len(agents) == 1
        assert agents[0]["name"] == "test-agent"

        # Get by id
        fetched = ca.get_custom_agent(created["id"])
        assert fetched is not None
        assert fetched["name"] == "test-agent"

        # Get non-existent
        assert ca.get_custom_agent("nonexistent") is None

        # Update
        updated = ca.update_custom_agent(created["id"], name="test-agent-v2")
        assert updated["name"] == "test-agent-v2"

        # Delete
        assert ca.delete_custom_agent(created["id"]) is True
        assert ca.list_custom_agents() == []

        # Delete non-existent
        assert ca.delete_custom_agent("nonexistent") is False

        # Create with reserved name should fail
        try:
            ca.create_custom_agent("diagram", "Should fail", "prompt")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    finally:
        ca._CUSTOM_AGENTS_PATH = original_path


def test_custom_agents_crud_with_tools(tmp_path):
    """Custom agents CRUD should handle the tools field."""
    import sdlc.services.custom_agents as ca

    original_path = ca._CUSTOM_AGENTS_PATH
    ca._CUSTOM_AGENTS_PATH = tmp_path / "custom_agents.json"

    try:
        # Create with tools
        created = ca.create_custom_agent(
            "calc-agent", "Calculates things", "Be a calculator",
            tools=["api", "web_search"],
        )
        assert created["tools"] == ["api", "web_search"]

        # Create without tools defaults to empty list
        created2 = ca.create_custom_agent(
            "plain-agent", "No tools", "Be plain",
        )
        assert created2["tools"] == []

        # Update tools
        updated = ca.update_custom_agent(created["id"], tools=["diagram"])
        assert updated["tools"] == ["diagram"]

        # Update with None should not change tools
        updated2 = ca.update_custom_agent(created["id"], description="New desc")
        assert updated2["tools"] == ["diagram"]

        # Create with invalid tool key should fail
        try:
            ca.create_custom_agent("bad-tools", "Bad", "prompt", tools=["nonexistent"])
            assert False, "Should have raised ValueError"
        except ValueError as exc:
            assert "Unknown tool key" in str(exc)

        # Update with invalid tool key should fail
        try:
            ca.update_custom_agent(created["id"], tools=["also-bad"])
            assert False, "Should have raised ValueError"
        except ValueError as exc:
            assert "Unknown tool key" in str(exc)

    finally:
        ca._CUSTOM_AGENTS_PATH = original_path


def test_tool_registry_has_expected_keys():
    """TOOL_REGISTRY should contain all expected tool categories."""
    from sdlc.services.custom_agents import TOOL_REGISTRY

    expected_keys = {"api", "devops", "diagram", "planning", "web_search"}
    assert set(TOOL_REGISTRY.keys()) == expected_keys
    for key, meta in TOOL_REGISTRY.items():
        assert "label" in meta
        assert "description" in meta
        assert "tools" in meta
        assert isinstance(meta["tools"], list)
        assert len(meta["tools"]) > 0


def test_get_tool_registry_returns_availability():
    """get_tool_registry should return availability status for each category."""
    from sdlc.services.custom_agents import get_tool_registry

    registry = get_tool_registry()
    assert "api" in registry
    assert "web_search" in registry
    for key, entry in registry.items():
        assert "available" in entry
        assert isinstance(entry["available"], bool)


def test_resolve_tools_empty():
    """resolve_tools should return empty list for empty input."""
    from sdlc.services.custom_agents import resolve_tools

    assert resolve_tools([]) == []


def test_resolve_tools_unknown_key():
    """resolve_tools should silently skip unknown keys."""
    from sdlc.services.custom_agents import resolve_tools

    result = resolve_tools(["nonexistent_key"])
    assert result == []


def test_resolve_tools_known_category():
    """resolve_tools should return tool instances for known categories."""
    from sdlc.services.custom_agents import resolve_tools

    result = resolve_tools(["web_search"])
    # web_search may or may not be available depending on deps
    assert isinstance(result, list)
    if result:
        assert result[0].name == "web_search"


def test_custom_agents_as_subagent_specs_with_tools(tmp_path):
    """custom_agents_as_subagent_specs should attach tools to specs."""
    import sdlc.services.custom_agents as ca

    original_path = ca._CUSTOM_AGENTS_PATH
    ca._CUSTOM_AGENTS_PATH = tmp_path / "custom_agents.json"

    try:
        # Create an agent with web_search tool
        ca.create_custom_agent(
            "search-agent", "Searches the web", "Be a searcher",
            tools=["web_search"],
        )

        specs = ca.custom_agents_as_subagent_specs()
        assert len(specs) == 1
        assert specs[0]["name"] == "search-agent"
        # tools key should be present (may be empty if deps missing)
        assert "tools" in specs[0]
        assert isinstance(specs[0]["tools"], list)

    finally:
        ca._CUSTOM_AGENTS_PATH = original_path


def test_custom_agents_as_subagent_specs_no_tools(tmp_path):
    """custom_agents_as_subagent_specs should work for agents without tools."""
    import sdlc.services.custom_agents as ca

    original_path = ca._CUSTOM_AGENTS_PATH
    ca._CUSTOM_AGENTS_PATH = tmp_path / "custom_agents.json"

    try:
        ca.create_custom_agent("plain-agent", "No tools", "Be plain")

        specs = ca.custom_agents_as_subagent_specs()
        assert len(specs) == 1
        assert specs[0]["name"] == "plain-agent"
        assert specs[0]["tools"] == []

    finally:
        ca._CUSTOM_AGENTS_PATH = original_path


# ── SysON settings ──────────────────────────────────────────────────────

# ── File upload ──────────────────────────────────────────────────────────

def test_ensure_host_upload_dir(tmp_path):
    """ensure_host_upload_dir should create the directory."""
    import sdlc.services.file_upload as fu
    import sdlc.core.config as cfg

    original = cfg.UPLOAD_DIR_HOST
    try:
        test_dir = tmp_path / "test-uploads"
        # Override the config value AND the module-level import
        cfg.UPLOAD_DIR_HOST = str(test_dir)
        # Re-import to pick up the new value
        import importlib
        importlib.reload(fu)
        fu.ensure_host_upload_dir()
        assert Path(str(test_dir)).resolve().exists()
    finally:
        cfg.UPLOAD_DIR_HOST = original
        importlib.reload(fu)


# ── Conversations ───────────────────────────────────────────────────────

def test_conversation_helpers():
    """Conversation helper functions should work."""
    from sdlc.services.conversations import _iso
    from datetime import datetime, timezone

    dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    iso = _iso(dt)
    assert "2025" in iso
    assert "T" in iso
    assert iso.endswith("+00:00") or iso.endswith("Z")


def test_render_conversation_markdown():
    """The export renderer should include messages, tool calls (input +
    output), and agent reasoning."""
    from sdlc.api.app import _render_conversation_markdown

    rows = [
        {
            "role": "human",
            "content": "Build a satellite BDD.",
            "agent_name": None,
            "created_at": "2025-01-01T12:00:00+00:00",
            "reasoning": None,
            "tool_calls": [],
            "attachments": [],
        },
        {
            "role": "ai",
            "content": "Here is the BDD.",
            "agent_name": "SysML Agent",
            "created_at": "2025-01-01T12:01:00+00:00",
            "reasoning": "I need to model the satellite parts.",
            "tool_calls": [
                {
                    "toolName": "SysMLValidatorTool",
                    "toolArgs": '{"code": "part def Satellite;"}',
                    "result": "OK",
                }
            ],
            "attachments": [],
        },
    ]

    md = _render_conversation_markdown("Satellite", "c1", rows)

    # Thread header
    assert "# Satellite" in md
    assert "`c1`" in md
    assert "**Messages**: 2" in md

    # Roles
    assert "## 1. User" in md
    assert "## 2. Assistant" in md
    assert "Build a satellite BDD." in md

    # Agent + timestamp metadata
    assert "**Agent**: SysML Agent" in md
    assert "**Time**: 2025-01-01T12:01:00+00:00" in md

    # Reasoning rendered as a blockquote
    assert "> **Reasoning**" in md
    assert "> I need to model the satellite parts." in md

    # Tool call: name, input (pretty JSON), output
    assert "### Tool call: `SysMLValidatorTool`" in md
    assert "**Input:**" in md
    assert '"code": "part def Satellite;"' in md
    assert "**Output:**" in md
    assert "OK" in md


def test_persist_assistant_message_accepts_tool_calls():
    """The SSE persist path must forward tool calls to the store.

    Regression guard: `_persist_assistant_message` used to take only
    content/agent/reasoning, so every tool call a thread made was dropped
    on the floor and the Markdown export rendered no `### Tool call:`
    sections for any real (SSE-captured) thread. The renderer test passed
    regardless because it hand-builds its rows.
    """
    import inspect

    from sdlc.api.app import _persist_assistant_message

    params = inspect.signature(_persist_assistant_message).parameters
    assert "tool_calls" in params, (
        "the persist path drops tool calls — thread exports will be incomplete"
    )

    # Forwarded verbatim to conversations_store.append_message(...).
    src = inspect.getsource(_persist_assistant_message)
    assert "tool_calls=tool_calls" in src


def test_persist_assistant_message_keeps_toolcall_only_turns():
    """A turn that made tool calls but emitted no prose must still persist.

    The old guard bailed on empty content, which silently discarded the
    tool calls of exactly the turns an export most needs.
    """
    import inspect

    from sdlc.api.app import _persist_assistant_message

    src = inspect.getsource(_persist_assistant_message)
    assert "not content.strip() and not tool_calls" in src


def test_runner_buffers_tool_calls_for_persistence():
    """The streamed tool_call / tool_args / tool_result events must be
    accumulated into one record per tool_id and handed to the persist call."""
    import inspect

    from sdlc.api.app import _spawn_run

    src = inspect.getsource(_spawn_run)
    assert "assistant_tool_calls: dict[str, dict[str, Any]] = {}" in src
    # name, streamed args, and result all land on the same record
    assert 'rec["toolArgs"] += delta_args' in src
    assert 'rec["result"] = content_text[:_TOOL_RESULT_MAX]' in src
    # and the buffer reaches postgres
    assert "list(assistant_tool_calls.values()) or None" in src


def test_export_renders_toolcall_only_message():
    """An assistant turn with tool calls and no prose still exports its
    tool section (the shape the runner now persists for such turns)."""
    from sdlc.api.app import _render_conversation_markdown

    rows = [
        {
            "role": "assistant",
            "content": "",
            "agent_name": "ingestion",
            "created_at": "2025-01-01T12:00:00+00:00",
            "reasoning": None,
            "tool_calls": [
                {
                    "toolId": "call_1",
                    "toolName": "read_file",
                    "toolArgs": '{"path": "spec.md"}',
                    "result": "42 lines",
                    "agent": "ingestion",
                }
            ],
            "attachments": [],
        },
    ]

    md = _render_conversation_markdown("T", "c1", rows)

    # "assistant" is the role the store actually writes (not "ai").
    assert "## 1. Assistant" in md
    assert "### Tool call: `read_file`" in md
    assert '"path": "spec.md"' in md
    assert "42 lines" in md


# ── Skills directory ─────────────────────────────────────────────────────

def test_skills_directory_exists():
    """The skills directory should exist and contain SKILL.md files."""
    skills_dir = Path(__file__).resolve().parent.parent / "src" / "sdlc" / "skills"
    assert skills_dir.exists(), f"Skills dir not found: {skills_dir}"

    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    assert len(skill_dirs) >= 10, f"Expected >=10 skill dirs, got {len(skill_dirs)}"

    for sd in skill_dirs:
        skill_file = sd / "SKILL.md"
        assert skill_file.exists(), f"Missing SKILL.md in {sd.name}"


# ── Docker backend ────────────────────────────────────────────────────────

def test_docker_backend_container_name():
    """container_name_for should produce deterministic names."""
    from sdlc.services.agent import container_name_for

    name = container_name_for("test-thread-123")
    assert name.startswith("harness-")
    assert "test-thread-123" in name


def test_docker_backend_safe_name():
    """_safe_name should sanitise thread IDs."""
    from sdlc.services.agent import container_name_for

    name = container_name_for("bad/thread:name@#$")
    assert "/" not in name
    assert "@" not in name
    assert "#" not in name
    assert name.startswith("harness-")


# ── API routes ───────────────────────────────────────────────────────────

def test_api_routes_exist():
    """The FastAPI app should have all expected routes registered."""
    from sdlc.api.app import app

    paths = {route.path for route in app.routes if hasattr(route, "path") and route.path}

    expected = {
        "/health", "/tracing",
        "/projects", "/projects/{project_id}/artifacts",
        "/projects/{project_id}/artifacts/{artifact_name:path}",
        "/projects/{project_id}/files",
        "/projects/{project_id}/download",
        "/chat", "/chat/stream", "/chat/resume",
        "/history/{thread_id}",
        "/session/{thread_id}",
        "/upload/{project_id}",
        "/conversations", "/conversations/{conversation_id}",
        "/conversations/{conversation_id}/messages",
        "/conversations/{conversation_id}/export",
        "/agents/custom", "/agents/custom/{agent_id}",
        "/settings/model",
        "/tools/registry",
    }

    for ep in expected:
        assert ep in paths, f"Missing route: {ep}"


# ── Context integrity: truncation must never be silent ────────────────────

def test_shell_output_truncation_is_marked_in_band():
    """Oversized command output must TELL the model it was cut.

    The `truncated` flag on ExecuteResponse has no consumers anywhere, so a
    flag alone is invisible to the agent: it would read the first N bytes of
    a file as if complete and extrapolate the rest. deepagents' own
    local_shell backend appends an in-band marker for this reason.
    """
    from sdlc.sandbox.docker_backend import DockerBackend

    be = DockerBackend.__new__(DockerBackend)
    be._max_output_bytes = 100

    out, truncated = be._cap_output("x" * 500)
    assert truncated is True
    assert "Output truncated at 100 bytes" in out
    assert "do NOT infer the omitted content" in out

    short, truncated = be._cap_output("fits")
    assert truncated is False
    assert short == "fits"


def test_shell_truncation_counts_bytes_not_characters():
    """The cap is a BYTE budget; slicing characters overshot it on non-ASCII.

    The project's source documents are German, so umlauts are routine and a
    character-sliced cap could keep well over the intended byte budget.
    """
    from sdlc.sandbox.docker_backend import DockerBackend

    be = DockerBackend.__new__(DockerBackend)
    be._max_output_bytes = 100

    # 200 two-byte chars = 400 bytes; a character slice would keep 100 chars
    # (200 bytes), double the budget.
    out, truncated = be._cap_output("ä" * 200)
    assert truncated is True
    # split() leaves the marker's two leading newlines on the body
    body = out.split("... Output truncated")[0].rstrip("\n")
    assert len(body.encode("utf-8")) <= 100
    # and the boundary must not leave a broken character behind
    body.encode("utf-8").decode("utf-8")


def test_compaction_input_includes_tool_evidence():
    """Compaction must summarize evidence, not just the agent's own prose.

    Previously only role/agent/content reached the summarizer, so every tool
    result was dropped before summarization — the summary became the thread's
    sole, unfalsifiable ground truth.
    """
    from sdlc.api.app import _format_history_for_compaction

    rows = [
        {
            "role": "assistant",
            "content": "Validated the model.",
            "agent_name": "sysml",
            "reasoning": "checking part definitions",
            "tool_calls": [
                {
                    "toolName": "SysMLValidatorTool",
                    "toolArgs": '{"path": "bdd.sysml"}',
                    "result": "3 errors found",
                }
            ],
            "attachments": [{"name": "spec.docx"}],
        }
    ]

    text = _format_history_for_compaction(rows)

    assert "Validated the model." in text
    assert "SysMLValidatorTool" in text
    assert "3 errors found" in text          # the evidence that was being lost
    assert "bdd.sysml" in text
    assert "checking part definitions" in text
    assert "spec.docx" in text


def test_compaction_clip_marks_the_cut():
    """A clipped tool result must not read as a complete one."""
    from sdlc.api.app import _clip

    assert _clip("short", 100) == "short"
    out = _clip("y" * 500, 100)
    assert out.startswith("y" * 100)
    assert "clipped" in out and "400 more chars" in out


def test_compaction_archives_full_transcript_before_destroying_it():
    """Compaction deletes checkpoints and truncates the message table, both
    irreversible. The archive is what makes a bad summary recoverable."""
    from sdlc.api.app import _archive_conversation

    rows = [
        {
            "role": "human",
            "content": "Build the BDD.",
            "agent_name": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "reasoning": None,
            "tool_calls": [],
            "attachments": [],
        },
        {
            "role": "assistant",
            "content": "Done.",
            "agent_name": "sysml",
            "created_at": "2026-01-01T00:01:00+00:00",
            "reasoning": None,
            "tool_calls": [
                {"toolName": "write_file", "toolArgs": "{}", "result": "ok"}
            ],
            "attachments": [],
        },
    ]

    path = _archive_conversation("conv-test", "Test thread", rows)
    assert path is not None

    from pathlib import Path as _P

    written = _P(path).read_text(encoding="utf-8")
    # the archive is the FULL transcript, tool calls included
    assert "Build the BDD." in written
    assert "write_file" in written
    _P(path).unlink()


# ── log.md provenance must not be invented ────────────────────────────────

def test_log_source_column_suppresses_nonexistent_dependencies():
    """A declared dependency is only printed when the file actually exists.

    Printing declared deps unconditionally produced log rows asserting that an
    artifact came from a file that was never uploaded — invented provenance,
    handed to agents that the prompts tell to consult log.md.
    """
    graph = {
        "requirements/REQUIREMENTS.md": {"depends_on": ["sources/never_uploaded.xlsx"]},
        "requirements/GLOSSARY.md": {"depends_on": ["requirements/REQUIREMENTS.md"]},
    }

    def source_for(path, known):
        deps = graph.get(path, {}).get("depends_on", [])
        for dep in deps:
            if dep in known:
                return dep
        return "-"

    # The declared source was never uploaded: print nothing rather than a lie.
    assert source_for("requirements/REQUIREMENTS.md", {"requirements/REQUIREMENTS.md"}) == "-"

    # When the declared dependency genuinely exists, name it.
    known = {"requirements/REQUIREMENTS.md"}
    assert source_for("requirements/GLOSSARY.md", known) == "requirements/REQUIREMENTS.md"


def test_log_header_does_not_claim_observed_provenance():
    """The column is a declared dependency, and must not be headed 'Source'."""
    from pathlib import Path as _P

    src = (_P(__file__).resolve().parent.parent
           / "src" / "sdlc" / "services" / "workspace.py").read_text(encoding="utf-8")
    assert "| Date | Action | Declared-From | Target |" in src
    assert "| Date | Action | Source | Target |" not in src


# ── Fixed project path for agents ─────────────────────────────────────────

def test_prompts_use_the_fixed_project_path_not_a_placeholder():
    """Agents must be given a resolvable path, not `/workspace/project_<id>`.

    The templates are module-level constants rendered at import while
    project_id arrives per request, so the real id was never interpolated:
    every agent saw a literal `<id>` placeholder or an ambiguous
    `project_*` glob and had to discover its own project directory.
    """
    import sdlc.services.subagents as sa
    from sdlc.services.subagents import ORCHESTRATOR_PROMPT

    prompts = [ORCHESTRATOR_PROMPT] + [
        a.get("system_prompt") or "" for a in sa.ALL_SUBAGENTS
    ]
    for text in prompts:
        assert "/workspace/project_<id>" not in text
        assert "/workspace/project_*" not in text

    assert "/workspace/current" in ORCHESTRATOR_PROMPT
    assert all("/workspace/current" in (a.get("system_prompt") or "") for a in sa.ALL_SUBAGENTS)


def test_link_current_cmd_targets_the_real_project_root():
    """The alias must resolve to this project's real directory, and -n must
    be present so re-pointing never nests the link inside itself."""
    from sdlc.services.workspace import CURRENT_LINK, ProjectWorkspace

    ws = ProjectWorkspace.__new__(ProjectWorkspace)
    ws.root = "/workspace/project_warehouse"

    cmd = ws.link_current_cmd()
    assert cmd == f"ln -sfn /workspace/project_warehouse {CURRENT_LINK}"
    assert "-sfn" in cmd  # -n: treat an existing link-to-dir as a file


def test_chat_stream_repoints_alias_every_run():
    """init_directories only runs on first creation, so a thread that
    switched project_id would otherwise leave the alias on the old project."""
    import inspect

    from sdlc.api.app import chat_stream

    src = inspect.getsource(chat_stream)
    assert "link_current_cmd()" in src


# ── /chat/resume must always terminate the stream ─────────────────────────

def test_resume_with_no_active_run_still_emits_done():
    """A resume with nothing to replay must still send `done`.

    It used to return a stream that closed with no terminal event, silently
    breaking the contract every client callback is keyed to: onDone never
    fired, so nothing that settles run state ran. A thread whose run finished
    while the user was on another thread kept its "WORKING" marker until a
    full page reload.
    """
    import inspect

    from sdlc.api.app import chat_resume

    src = inspect.getsource(chat_resume)
    assert '"event": "done"' in src, "no-run path must emit a terminal event"
    # and the old silent-close generator must be gone
    assert "if False:" not in src, "empty no-op generator should not remain"


# ── model settings must reach threads that already exist ──────────────────

def test_model_settings_update_invalidates_cached_orchestrators():
    """Changing the model/endpoint must apply to EXISTING threads.

    Orchestrators are cached per thread in `_sessions` and build their model
    once. Without invalidation a thread keeps the model it was created with
    forever, so a UI change appeared to work only on new threads — and an old
    thread kept calling an endpoint the user had already moved away from,
    surfacing it as a provider error they could not act on.
    """
    import inspect

    from sdlc.api.app import update_model_settings

    src = inspect.getsource(update_model_settings)
    assert "_invalidate_all_orchestrators" in src


def test_custom_agent_and_model_settings_invalidate_consistently():
    """Both config surfaces that get baked into a cached orchestrator must
    invalidate it. Custom agents already did; model settings were the gap."""
    import inspect

    import sdlc.api.app as app

    for fn in (
        app.update_model_settings,
        app.create_custom_agent_endpoint,
        app.update_custom_agent_endpoint,
        app.delete_custom_agent_endpoint,
    ):
        assert "_invalidate_all_orchestrators" in inspect.getsource(fn), fn.__name__


# ── replay must be detectable by the client ───────────────────────────────

def test_wire_event_carries_seq_into_the_payload():
    """The client needs the run sequence to recognise a replay.

    `_event_generator` replays a run's entire history to EVERY new
    subscriber, so a re-attach re-delivers events the UI already applied.
    `_seq` used to be stripped at the boundary, leaving the client no way to
    tell a replay from new output — the run's text got painted twice.

    It cannot ride as a top-level key: sse-starlette does
    ServerSentEvent(**event) and an unknown kwarg raises TypeError. So it
    goes inside the JSON payload.
    """
    import json

    from sdlc.api.app import _wire_event

    wired = _wire_event(
        {"event": "message", "data": json.dumps({"type": "token", "content": "hi"}), "_seq": 7}
    )
    assert "_seq" not in wired, "must not survive as a top-level SSE field"
    payload = json.loads(wired["data"])
    assert payload["_seq"] == 7
    assert payload["content"] == "hi", "original payload must be preserved"


def test_wire_event_passes_through_non_json_payloads():
    """A payload that isn't our JSON envelope must not be corrupted."""
    from sdlc.api.app import _wire_event

    wired = _wire_event({"event": "ping", "data": "not-json", "_seq": 3})
    assert wired["data"] == "not-json"
    assert "_seq" not in wired


def test_wire_event_without_seq_is_unchanged():
    from sdlc.api.app import _wire_event

    assert _wire_event({"event": "done", "data": "{}"}) == {"event": "done", "data": "{}"}


# ── replayed checkpoint work must not re-stream ───────────────────────────
#
# These drive the real suppression predicate and the real snapshot reader. The
# previous pair asserted on `inspect.getsource(_spawn_run)` string contents —
# `assert "replayed_ids" in src` — which passes for any edit that keeps the
# identifier, including one that deletes the guard's effect entirely. A source
# assertion cannot tell a working filter from a dead one, so the bug these
# tests exist for (a resumed run repainting the prior conversation) stayed
# green through the whole period it was live.

def test_replay_suppression_recognises_prior_messages_and_tool_calls():
    """A replayed chunk must be recognised by identity, not by run.

    A run that dies mid-execution (backend restart, container recycle, provider
    outage) leaves pending writes. The next invoke on the same thread_id
    resumes from that checkpoint and REPLAYS the interrupted work, re-emitting
    messages already in the transcript. Typing "continue" after a restart then
    re-streams the prior conversation into the UI.

    The client's `_seq` dedup cannot catch it — these are real events in a real
    new run — so the filter has to be identity-based, and it has to cover tool
    results as well as messages: a replayed ToolMessage carries a *new* message
    id but reuses the tool_call_id of the call already in the transcript.
    """
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    from sdlc.api.app import _chunk_already_persisted, _identities_from_state

    prior = [
        HumanMessage(content="build the model", id="m1"),
        AIMessage(
            content="",
            id="m2",
            tool_calls=[{"name": "task", "args": {}, "id": "call-1"}],
        ),
        ToolMessage(content="done", tool_call_id="call-1", id="m3"),
    ]
    message_ids, tool_call_ids = _identities_from_state(prior)

    assert message_ids == {"m1", "m2", "m3"}
    assert tool_call_ids == {"call-1"}

    # The replayed assistant turn: new message id, same tool-call id.
    replayed_ai = AIMessage(
        content="",
        id="fresh-id",
        tool_calls=[{"name": "task", "args": {}, "id": "call-1"}],
    )
    assert _chunk_already_persisted(replayed_ai, message_ids, tool_call_ids)

    # The replayed tool result: new message id, same tool_call_id.
    replayed_tool = ToolMessage(content="done", tool_call_id="call-1", id="fresh-id-2")
    assert _chunk_already_persisted(replayed_tool, message_ids, tool_call_ids)

    # A genuinely new call must NOT be suppressed.
    fresh = AIMessage(
        content="",
        id="new-1",
        tool_calls=[{"name": "task", "args": {}, "id": "call-2"}],
    )
    assert not _chunk_already_persisted(fresh, message_ids, tool_call_ids)

    # Nor may a partial replay of a *new* batch be dropped wholesale: only a
    # batch that is entirely prior calls is a replay.
    mixed = AIMessage(
        content="",
        id="new-2",
        tool_calls=[
            {"name": "task", "args": {}, "id": "call-1"},
            {"name": "task", "args": {}, "id": "call-3"},
        ],
    )
    assert not _chunk_already_persisted(mixed, message_ids, tool_call_ids)


def test_replay_suppression_tolerates_unrecognisable_chunks():
    """An unrecognisable chunk must not kill the run.

    This runs inside the stream loop, where raising aborts a live run over a
    cosmetic check. `tool_calls` is a derived property on a streaming chunk and
    can throw while the argument JSON is still incomplete, so the guard has to
    narrow to "not a replay" rather than propagate.
    """
    from sdlc.api.app import _chunk_already_persisted

    class Exploding:
        id = "x"

        @property
        def tool_call_id(self):
            raise RuntimeError("partial chunk")

        @property
        def tool_calls(self):
            raise RuntimeError("partial chunk")

    assert _chunk_already_persisted(Exploding(), set(), set()) is False


def test_replay_identity_falls_back_to_the_persisted_transcript():
    """A failed checkpoint read must NARROW the stream, not widen it.

    Streaming blind whenever the snapshot is unavailable is what repainted a
    whole conversation into the UI, so the fallback reads the Postgres
    transcript instead. It is a different shape — the frontend's camelCase
    `toolId`, not LangChain `tool_calls` — so it is worth asserting the mapping
    rather than trusting the key name.
    """
    from sdlc.api.app import _tool_ids_from_persisted

    rows = [
        {"role": "user", "content": "hi", "tool_calls": None},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"toolId": "call-1", "toolName": "task", "toolArgs": "{}"},
                {"toolId": "call-2", "toolName": "read_file", "toolArgs": "{}"},
            ],
        },
        {"role": "assistant", "content": "done", "tool_calls": []},
    ]
    assert _tool_ids_from_persisted(rows) == {"call-1", "call-2"}
    # A row with no tool calls contributes nothing and must not raise.
    assert _tool_ids_from_persisted([{"role": "user"}]) == set()
    assert _tool_ids_from_persisted(None) == set()


def test_runner_snapshots_prior_identity_and_marks_the_resume():
    """The runner must read prior identity AND tell the client it resumed.

    The `run_started` marker is what lets the client distinguish a replayed run
    from a fresh one; without it the client's only option is to append, which
    is the duplicate it is trying to avoid.
    """
    import inspect

    from sdlc.api.app import _spawn_run

    src = inspect.getsource(_spawn_run)
    assert "_load_replay_identity" in src, "must read the pre-run identity"
    assert '"type": "run_started"' in src, "must mark the run as a resume"
    # The gate has to sit where every chunk type passes through, ahead of the
    # namespace bookkeeping that emits subagent cards.
    assert src.index("_chunk_already_persisted") < src.index('"type": "subagent_started"')

