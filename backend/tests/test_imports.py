"""Tests for the SDLC Agent Orchestrator — restructured imports."""

from __future__ import annotations


def test_import_docker_backend():
    """DockerBackend should be importable and implement all abstract methods."""
    from deepagents.backends.sandbox import BaseSandbox
    from sdlc.sandbox.docker_backend import DockerBackend

    assert issubclass(DockerBackend, BaseSandbox)

    for cls in BaseSandbox.__mro__:
        if hasattr(cls, "__abstractmethods__"):
            for name in cls.__abstractmethods__:
                method = getattr(DockerBackend, name)
                assert not getattr(method, "__isabstractmethod__", False), (
                    f"{name} is still abstract"
                )


def test_import_config():
    """Config module should load with NHR defaults."""
    import sdlc.core.config as cfg

    assert cfg.MODEL_NAME  # defaults to an NHR model
    assert cfg.OPENAI_BASE_URL  # defaults to NHR gateway
    assert cfg.HOST
    assert isinstance(cfg.PORT, int)


def test_invocation_budget_config_default_off():
    """R2: SDLC_MAX_LLM_INVOCATIONS defaults to 0 (cap disabled on live chat).

    The 20-trial CostEvals batch peaked at 88 LLM invocations (median 71);
    the cap is opt-in via env so live chats stay unbounded while eval runs
    can bound worst-case cost above the observed max.
    """
    import sdlc.core.config as cfg

    assert isinstance(cfg.SDLC_MAX_LLM_INVOCATIONS, int)
    assert cfg.SDLC_MAX_LLM_INVOCATIONS == 0


def test_invocation_budget_middleware_constructible():
    """R2: ModelCallLimitMiddleware (the invocation budget) imports and
    constructs with the eva-run semantics (run_limit, exit_behavior='end')."""
    from langchain.agents.middleware import ModelCallLimitMiddleware

    m = ModelCallLimitMiddleware(run_limit=100, exit_behavior="end")
    assert m is not None

    # env override path: config reads int from env
    import os

    import sdlc.core.config as cfg

    os.environ["SDLC_MAX_LLM_INVOCATIONS"] = "100"
    try:
        import importlib

        cfg = importlib.reload(cfg)
        assert cfg.SDLC_MAX_LLM_INVOCATIONS == 100
    finally:
        os.environ.pop("SDLC_MAX_LLM_INVOCATIONS", None)
        importlib.reload(cfg)
        assert cfg.SDLC_MAX_LLM_INVOCATIONS == 0


def test_import_schemas():
    """Pydantic schemas should instantiate with defaults."""
    from sdlc.models.schemas import (
        ArtifactListResponse,
        ChatRequest,
        ChatResponse,
        HealthResponse,
        ProjectCreateResponse,
        TracingStatusResponse,
        UploadResponse,
    )

    req = ChatRequest(message="Hello")
    assert req.thread_id == "default"
    assert req.project_id == "default"
    assert req.uploaded_files == []

    resp = ChatResponse(message="Hi", thread_id="default", project_id="default")
    assert resp.message == "Hi"

    proj = ProjectCreateResponse(project_id="test", root="/workspace/project_test")
    assert proj.status == "created"


def test_import_agent():
    """Agent module (factory + subagent defs) should be importable."""
    from sdlc.services.agent import (
        create_orchestrator,
        init_checkpointer,
        close_checkpointer,
        container_name_for,
    )

    assert callable(create_orchestrator)
    assert callable(init_checkpointer)
    assert callable(close_checkpointer)
    assert callable(container_name_for)
    assert "harness-" in container_name_for("test-thread")


def test_import_subagents():
    """Subagent definitions should be importable from subagents module."""
    from sdlc.services.subagents import ALL_SUBAGENTS, ORCHESTRATOR_PROMPT

    assert len(ALL_SUBAGENTS) == 7

    for sa in ALL_SUBAGENTS:
        assert "name" in sa
        assert "description" in sa
        assert "system_prompt" in sa

    assert "@Ingestion" in ORCHESTRATOR_PROMPT
    assert "@Requirements" in ORCHESTRATOR_PROMPT
    assert "@Architecture" in ORCHESTRATOR_PROMPT
    assert "@API" in ORCHESTRATOR_PROMPT
    assert "@Planning" in ORCHESTRATOR_PROMPT
    assert "@DevOps" in ORCHESTRATOR_PROMPT
    assert "@Diagram" in ORCHESTRATOR_PROMPT


def test_import_workspace():
    """Workspace module should be importable with DAG and agent mappings."""
    from sdlc.services.workspace import (
        AGENT_ARTIFACTS,
        ARTIFACT_AGENT,
        DEFAULT_PROJECT_GRAPH,
        ProjectWorkspace,
    )

    # Every agent has at least one artifact, EXCEPT layout which writes
    # to the host filesystem (Visio COM on Windows) and intentionally
    # has an empty list.
    for agent, artifacts in AGENT_ARTIFACTS.items():
        if agent == "layout":
            continue  # Visio outputs go to host, not sandbox
        assert len(artifacts) > 0, f"{agent} has no artifacts"

    # Reverse mapping is consistent
    for artifact, agent in ARTIFACT_AGENT.items():
        assert agent in AGENT_ARTIFACTS

    # Dependency graph has entries
    assert len(DEFAULT_PROJECT_GRAPH) > 0


def test_import_artifacts():
    """Artifact schemas and templates should be importable."""
    from sdlc.services.artifacts import ARTIFACT_SCHEMAS, get_schema_prompt

    assert "REQUIREMENTS.md" in ARTIFACT_SCHEMAS
    assert "ARCHITECTURE.md" in ARTIFACT_SCHEMAS
    assert "openapi.yaml" in ARTIFACT_SCHEMAS

    prompt = get_schema_prompt("class.mmd")
    assert prompt


def test_import_app():
    """FastAPI app should be importable and have expected routes."""
    from sdlc.api.app import app

    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/health" in paths
    assert "/chat" in paths
    assert "/chat/stream" in paths
    assert "/upload/{project_id}" in paths or "/projects" in paths
    assert "/projects" in paths
    assert "/tracing" in paths


def test_tracing_module():
    """Tracing module should be importable and helpers should work."""
    from sdlc.core.tracing import (
        is_tracing_enabled,
        make_trace_metadata,
        setup_tracing,
    )

    # setup_tracing returns a dict with expected keys
    info = setup_tracing()
    assert isinstance(info, dict)
    assert "tracing_enabled" in info
    assert "status" in info

    # make_trace_metadata works
    meta = make_trace_metadata("proj1", "thread1", agent_name="ingestion")
    assert meta["project_id"] == "proj1"
    assert meta["subagent"] == "ingestion"

    # is_tracing_enabled returns bool
    assert isinstance(is_tracing_enabled(), bool)


def test_docker_backend_instantiation():
    """DockerBackend can be instantiated without Docker running (lazy init)."""
    from sdlc.sandbox.docker_backend import DockerBackend

    backend = DockerBackend(
        image="python:3.12-slim",
        auto_create=False,
        container_id="fake-id",
    )
    assert backend.id  # container name is generated
    backend.close()


def test_build_model():
    """_build_model should create a ChatOpenAI instance."""
    import sdlc.core.config
    from sdlc.services.agent import _build_model
    from langchain_openai import ChatOpenAI

    model = _build_model()
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == sdlc.core.config.MODEL_NAME


def test_build_model_sets_summarization_profile():
    """_build_model declares a context window ONLY when one is configured.

    deepagents picks fraction-based summarization triggers (0.85/0.10) when a
    profile is present and a conservative fixed 170K trigger when it is not.

    The value must describe the endpoint OPENAI_BASE_URL actually points at,
    so it is configuration, not a constant. It was hardcoded — first to
    128_000 (8x too small for deepseek-v4-flash, causing compaction at 11% of
    capacity) and then to 1_048_576, which is correct for that model on Ollama
    and wrong for every other endpoint. Over-declaring is the worse of the two
    errors: the trigger lands above the provider's real limit, so
    summarization never fires and the request hard-errors on overflow.

    Unset therefore means "unknown" and must leave the profile alone.
    """
    from sdlc.services import model_settings
    from sdlc.services.agent import _build_model
    from langchain_openai import ChatOpenAI

    def mock_get_effective_settings():
        return {
            "model_provider": "openai",
            "reasoning_effort": "",
            "agent_model": "deepseek-v4-flash:cloud",
            "base_url": "http://localhost:11434/v1",
            "api_key": "fake-key",
            "vision_model": "",
            "retry_model": "",
        }

    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setattr(model_settings, "get_effective_settings", mock_get_effective_settings)
    try:
        model = _build_model()
        assert isinstance(model, ChatOpenAI)
        # Unset (the default) must NOT invent a window for an unknown endpoint.
        import sdlc.services.agent as _agent
        if _agent.SDLC_MAX_INPUT_TOKENS == 0:
            assert not model.profile, "must not declare a window it cannot know"
        else:
            assert model.profile.get("max_input_tokens") == _agent.SDLC_MAX_INPUT_TOKENS
    finally:
        monkeypatch.undo()


def test_build_model_nvidia(monkeypatch):
    """_build_model should create a ChatNVIDIA instance when provider is nvidia."""
    from sdlc.services import model_settings
    from sdlc.services.agent import _build_model
    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    def mock_get_effective_settings():
        return {
            "model_provider": "nvidia",
            "reasoning_effort": "medium",
            "agent_model": "minimaxai/minimax-m3",
            "base_url": "",
            "api_key": "fake-key",
            "vision_model": "minimaxai/minimax-m3",
            "retry_model": "",
        }

    monkeypatch.setattr(model_settings, "get_effective_settings", mock_get_effective_settings)
    model = _build_model()
    assert isinstance(model, ChatNVIDIA)
    assert model.model == "minimaxai/minimax-m3"
    assert model.model_kwargs.get("reasoning_effort") == "medium"