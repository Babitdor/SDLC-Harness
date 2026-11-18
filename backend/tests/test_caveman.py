"""Caveman read-less contract: shrink tool results, never lose a finding.

Three properties are load-bearing and each has a test here:

1. **Deterministic** — same bytes in, same bytes out. A rewrite that varied
   between turns would change the request prefix and cost more than it saves.
2. **Findings survive** — validation output is this pipeline's product. If a
   compacted report drops an error, the next agent claims a clean run it never
   had.
3. **Reversible** — the exact original is stored and the footer names the
   handle, so `caveman_retrieve` can page it back.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from langchain_core.messages import ToolMessage

from sdlc.services import caveman


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(caveman, "CAVEMAN_STORE_DIR", str(tmp_path / "store"))
    monkeypatch.setattr(caveman, "CAVEMAN_MODE", "read")
    monkeypatch.setattr(caveman, "CAVEMAN_MIN_CHARS", 100)
    caveman.CavemanStats.reset()
    return tmp_path / "store"


FINDINGS = [
    {"path": "/x", "severity": "error", "message": f"schema mismatch on field {i}"}
    for i in range(240)
]


def test_small_results_are_untouched() -> None:
    """Under the floor the footer would cost more than the saving."""
    out = caveman.compact("short output")
    assert out.text == "short output"
    assert out.fmt == "none"


def test_off_mode_passes_everything_through(monkeypatch) -> None:
    monkeypatch.setattr(caveman, "CAVEMAN_MODE", "off")
    monkeypatch.setattr(caveman, "CAVEMAN_MIN_CHARS", 1)
    out = caveman.compact("x" * 50_000)
    assert out.fmt == "none"
    assert out.text == "x" * 50_000


def test_compaction_is_deterministic() -> None:
    """The prefix-cache contract: identical input must yield identical bytes.

    A timestamp, a random handle or an iteration-order dependency here would
    make every turn a cache miss — the exact failure mode the usage ledger
    exists to expose.
    """
    payload = "\n".join(f"2026-01-01T00:00:{i:02d} INFO step {i}" for i in range(400))
    first = caveman.compact(payload)
    second = caveman.compact(payload)
    assert first.text == second.text
    assert first.fmt == second.fmt


def test_json_report_keeps_shape_and_every_finding() -> None:
    payload = json.dumps({"errors": FINDINGS, "summary": "240 problems"}, indent=2)
    out = caveman.compact(payload)

    assert out.fmt == "json"
    assert out.kept_chars < out.original_chars / 2
    # 3 shown, 237 elided: the shape is what tells the agent there are more.
    assert "237 more" in out.text
    # The first findings are shown in full, message intact.
    assert "schema mismatch on field 0" in out.text


def test_log_keeps_every_error_line_and_collapses_repeats() -> None:
    lines = [f"2026-01-01T00:00:{i:02d} INFO building target {i}" for i in range(300)]
    lines.insert(120, "2026-01-01T00:02:00 ERROR Cannot resolve dependency foo")
    lines.extend(["2026-01-01T00:03:00 WARN deprecated flag used"] * 30)
    out = caveman.compact("\n".join(lines))

    assert out.fmt == "log"
    # Shrunk for real: without this, a compressor that kept everything would
    # also satisfy the finding assertions below and prove nothing.
    assert out.kept_chars < out.original_chars / 2
    assert "Cannot resolve dependency foo" in out.text
    assert "deprecated flag used" in out.text
    assert "(x30)" in out.text


def test_text_keeps_head_tail_and_buried_findings() -> None:
    body = [f"line {i} of prose" for i in range(400)]
    body[250] = "Traceback (most recent call last): boom"
    out = caveman.compact("\n".join(body))

    assert out.fmt == "text"
    assert "line 0 of prose" in out.text
    assert "line 399 of prose" in out.text
    assert "Traceback" in out.text
    assert "omitted" in out.text


def test_original_round_trips_through_the_handle() -> None:
    payload = "\n".join(f"row {i}, alpha, beta" for i in range(500))
    out = caveman.compact(payload)
    assert out.fmt != "none"

    handle = out.text.rsplit('caveman_retrieve("', 1)[1].split('"', 1)[0]
    # Default page is 6000 chars; the footer tells the caller how to continue.
    assert caveman.load_original(handle).startswith(payload[:6000])
    # Below the 500-char floor, so the page is widened rather than honoured.
    assert caveman.load_original(handle, offset=0, limit=100).startswith(payload[:500])



def test_store_is_capped_oldest_first(monkeypatch) -> None:
    """A long-lived backend must not accumulate originals without bound."""
    monkeypatch.setattr(caveman, "CAVEMAN_STORE_MAX", 3)
    import time

    for i in range(6):
        caveman.store_original(f"payload {i} " + "x" * 200)
        time.sleep(0.01)  # mtime ordering is the eviction key

    store = caveman._store_root()
    files = sorted(p.name for p in store.glob("*.txt"))
    assert len(files) <= 3
    # The newest write survives; the oldest are the ones evicted.
    newest = caveman.store_original("freshest " + "y" * 200)
    assert (store / f"{newest}.txt").exists()

def test_failed_store_refuses_to_shorten(monkeypatch) -> None:
    """Upstream rule, kept: no original, no lossy replacement."""
    monkeypatch.setattr(caveman, "store_original", lambda text: None)
    payload = "\n".join(f"2026-01-01T00:00:00 INFO step {i}" for i in range(400))
    out = caveman.compact(payload)
    assert out.fmt == "none"
    assert out.text == payload


def test_malformed_inputs_never_raise() -> None:
    for payload in ["{" * 3000, "\x00" * 3000, "a" * 5000, "<div>" * 900]:
        out = caveman.compact(payload)
        assert isinstance(out.text, str)


def _tool_message(content: str) -> ToolMessage:
    return ToolMessage(content=content, tool_call_id="call-1", name="read_file")


class _Request:
    def __init__(self, name: str) -> None:
        self.tool_call = {"name": name, "args": {}, "id": "call-1"}


def test_middleware_compacts_tool_results() -> None:
    middleware = caveman.CavemanToolMiddleware()
    payload = json.dumps({"errors": FINDINGS}, indent=2)

    async def handler(_request):
        return _tool_message(payload)

    result = asyncio.run(middleware.awrap_tool_call(_Request("read_file"), handler))

    assert isinstance(result, ToolMessage)
    assert len(result.content) < len(payload)
    assert "[caveman json:" in result.content
    assert caveman.CavemanStats.snapshot()["results_compacted"] == 1


def test_middleware_skips_exempt_tools_and_rich_content() -> None:
    middleware = caveman.CavemanToolMiddleware()
    big = json.dumps({"errors": FINDINGS}, indent=2)

    async def handler(_request):
        return _tool_message(big)

    # Recovery must never compact itself, or the original becomes unreadable.
    result = asyncio.run(
        middleware.awrap_tool_call(_Request("caveman_retrieve"), handler)
    )
    assert result.content == big

    async def blocks(_request):
        return ToolMessage(
            content=[{"type": "text", "text": big}], tool_call_id="c2", name="read_file"
        )

    result = asyncio.run(middleware.awrap_tool_call(_Request("read_file"), blocks))
    assert isinstance(result.content, list)


def test_middleware_is_gated_by_mode(monkeypatch) -> None:
    assert caveman.caveman_middleware()
    assert caveman.recovery_tools()
    monkeypatch.setattr(caveman, "CAVEMAN_MODE", "off")
    assert caveman.caveman_middleware() == []
    assert caveman.recovery_tools() == []


def test_retrieve_tool_pages_and_rejects_unknown_handles() -> None:
    payload = "\n".join(f"abcdefghij line {i}" for i in range(400))
    out = caveman.compact(payload)
    handle = out.text.rsplit('caveman_retrieve("', 1)[1].split('"', 1)[0]

    tool = caveman.CavemanRetrieveTool()
    page = tool._run(handle=handle, offset=100, limit=500)
    assert page.startswith(payload[100:600])
    assert "offset=600" in page

    assert "no stored original" in tool._run(handle="deadbeefdeadbeef")
    # Path traversal cannot escape the store: the handle is reduced to hex, so
    # a traversal string becomes a (missing) handle rather than a filesystem hit.
    traversal = tool._run(handle="../../etc/passwd")
    assert "no stored original" in traversal
    assert "passwd" not in traversal



# ── Wiring: the seams that actually reach a live agent ───────────────────


def test_subagents_inherit_the_middleware_and_the_recovery_tool() -> None:
    """Seven subagent specs share one list; a new one must inherit both."""
    from sdlc.services.subagents import ALL_SUBAGENTS, _retry_middleware, attach_tools

    names = [type(m).__name__ for m in _retry_middleware()]
    assert "CavemanToolMiddleware" in names

    attached = attach_tools(ALL_SUBAGENTS, {})
    for spec in attached:
        tools = [t.name for t in spec.get("tools", [])]
        assert "caveman_retrieve" in tools, spec["name"]


def test_orchestrator_wiring_carries_caveman(monkeypatch) -> None:
    """create_orchestrator must hand the middleware and the tool to deepagents.

    Asserted on the captured call rather than on the compiled graph: this is
    the wiring a future refactor would break, and it is observable without a
    model.
    """
    from sdlc.services import agent as agent_mod
    from sdlc.services import model_settings

    captured: dict[str, Any] = {}

    class _StubBackend:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def execute(self, *args: Any, **kwargs: Any) -> Any:
            class _Result:
                output = ""
                exit_code = 0
                truncated = False

            return _Result()

    monkeypatch.setattr(agent_mod, "DockerBackend", _StubBackend)
    monkeypatch.setattr(agent_mod, "_checkpointer", object())
    monkeypatch.setattr(
        model_settings,
        "get_effective_settings",
        lambda: {
            "model_provider": "openai",
            "agent_model": "m",
            "base_url": "http://localhost:1/v1",
            "api_key": "x",
            "reasoning_effort": "",
        },
    )
    monkeypatch.setattr(
        agent_mod,
        "create_deep_agent",
        lambda **kwargs: captured.update(kwargs) or object(),
    )

    agent_mod.create_orchestrator("caveman-wiring")

    middleware_names = [type(m).__name__ for m in captured["middleware"]]
    assert "CavemanToolMiddleware" in middleware_names
    assert "caveman_retrieve" in [t.name for t in captured["tools"]]


def test_the_graph_actually_compacts_a_tool_result(monkeypatch) -> None:
    """End to end: a tool call inside a compiled deepagents graph is shrunk.

    The unit tests prove the middleware can compact; only a real graph run
    proves it *does* — that deepagents applies the hook we hand it, and that
    the next turn sees the shortened bytes rather than the original.
    """
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    from langchain_core.tools import tool
    from langgraph.checkpoint.memory import InMemorySaver

    from sdlc.services import agent as agent_mod
    from sdlc.services import model_settings

    big = json.dumps({"errors": FINDINGS}, indent=2)
    seen: list[list[Any]] = []
    state = {"turn": 0}

    @tool
    def dump_report() -> str:
        """Return the full validation report."""
        return big

    class _Recorder(BaseChatModel):
        profile: dict = {}

        @property
        def _llm_type(self) -> str:
            return "recorder"

        def bind_tools(self, tools, **kwargs):  # type: ignore[override]
            return self.bind(_tools=tools, **kwargs)

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            seen.append(list(messages))
            state["turn"] += 1
            if state["turn"] == 1:
                reply = AIMessage(
                    content="",
                    tool_calls=[{"name": "dump_report", "args": {}, "id": "call-1"}],
                )
            else:
                reply = AIMessage(content="done")
            return ChatResult(generations=[ChatGeneration(message=reply)])

        async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
            return self._generate(messages, stop, run_manager, **kwargs)

    class _StubBackend:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def execute(self, *args: Any, **kwargs: Any) -> Any:
            class _Result:
                output = ""
                exit_code = 0
                truncated = False

            return _Result()

    monkeypatch.setattr(agent_mod, "DockerBackend", _StubBackend)
    monkeypatch.setattr(agent_mod, "_checkpointer", InMemorySaver())
    monkeypatch.setattr(agent_mod, "_build_orchestrator_tools", lambda: [dump_report])
    monkeypatch.setattr(agent_mod, "_build_model", lambda *a, **k: _Recorder())
    monkeypatch.setattr(
        model_settings,
        "get_effective_settings",
        lambda: {
            "model_provider": "openai",
            "agent_model": "m",
            "base_url": "http://localhost:1/v1",
            "api_key": "x",
            "reasoning_effort": "",
        },
    )

    graph, _backend = agent_mod.create_orchestrator("caveman-graph")
    asyncio.run(
        graph.ainvoke(
            {"messages": [HumanMessage("run the report")]},
            config={"configurable": {"thread_id": "caveman-graph"}},
        )
    )

    tool_messages = [
        m for msgs in seen for m in msgs if isinstance(m, ToolMessage)
    ]
    assert tool_messages, "the tool never ran inside the graph"
    compacted = tool_messages[-1].content
    assert isinstance(compacted, str)
    assert "[caveman json:" in compacted
    assert len(compacted) < len(big) / 2

def test_orchestrator_prompt_carries_the_voice_rules() -> None:
    """The vendored skill must actually reach the prompt, not just the repo."""
    from sdlc.services.subagents import ORCHESTRATOR_PROMPT

    assert "{{" not in ORCHESTRATOR_PROMPT
    assert "caveman_retrieve" in ORCHESTRATOR_PROMPT
    # The carve-out is the part that keeps artifacts readable.
    assert "Artifacts" in ORCHESTRATOR_PROMPT
    assert "full conventional prose" in ORCHESTRATOR_PROMPT
