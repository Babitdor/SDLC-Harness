"""Prompt-cache contract: the request prefix must stay byte-stable.

Prompt caching is a *prefix* cache on the provider side. It only pays while
the bytes at the front of a request are identical to a request it already
saw: the system prompt, then the tool schemas, then the earlier messages.
One timestamp, one reordered tool, one dict that serialises differently and
every later call in the thread is a miss — silently, with no error, and the
only symptom is the token bill.

That is what these tests defend. They do not assert that a provider caches
(that is the provider's business, and unobservable offline); they assert the
precondition this codebase controls.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class _Recorder(BaseChatModel):
    """Chat model that records exactly what a caller sent, then answers once."""

    profile: dict = {}

    @property
    def _llm_type(self) -> str:
        return "recorder"

    def bind_tools(self, tools, **kwargs):  # type: ignore[override]
        return self.bind(_tools=tools, **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tools = kwargs.pop("_tools", [])
        RECORDED.append({"messages": list(messages), "tools": list(tools)})
        # Real providers report usage on the message; the ledger test below
        # depends on that shape, not on a stub.
        message = AIMessage(
            content="ok",
            usage_metadata={
                "input_tokens": 4000,
                "output_tokens": 20,
                "total_tokens": 4020,
                "input_token_details": {"cache_read": 3500},
            },
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop, run_manager, **kwargs)


RECORDED: list[dict[str, Any]] = []


def _canon(obj: Any) -> str:
    def norm(o: Any) -> Any:
        if isinstance(o, dict):
            return {k: norm(v) for k, v in sorted(o.items())}
        if isinstance(o, (list, tuple)):
            return [norm(v) for v in o]
        return o

    return json.dumps(norm(obj), sort_keys=True, default=str)


def _body(message: Any) -> str:
    content = getattr(message, "content", "")
    return content if isinstance(content, str) else _canon(content)


def _prefix(record: dict[str, Any]) -> str:
    """The cacheable prefix of one request: system prompt + tool schemas."""
    return _canon(
        {
            "system": _body(record["messages"][0]),
            "tools": [
                [getattr(t, "name", ""), _canon(getattr(t, "args", {}))]
                for t in record["tools"]
            ],
        }
    )


@pytest.fixture()
def built_agent(monkeypatch):
    """create_orchestrator with a recording model and no Docker side effects."""
    from langgraph.checkpoint.memory import InMemorySaver

    from sdlc.services import agent as agent_mod
    from sdlc.services import model_settings
    from sdlc.services.usage import UsageLedger, UsageRecordingHandler

    UsageLedger.reset()
    class _StubBackend:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.container_name = kwargs.get("container_name", "stub")

        def execute(self, *args: Any, **kwargs: Any) -> Any:
            class _Result:
                output = ""
                exit_code = 0
                truncated = False

            return _Result()

    RECORDED.clear()
    monkeypatch.setattr(agent_mod, "DockerBackend", _StubBackend)
    monkeypatch.setattr(agent_mod, "_checkpointer", InMemorySaver())
    monkeypatch.setattr(
        model_settings,
        "get_effective_settings",
        lambda: {
            "model_provider": "openai",
            "agent_model": "prefix-model",
            "base_url": "http://localhost:1/v1",
            "api_key": "x",
            "reasoning_effort": "",
        },
    )
    def _fake_build_model(thread_id: str | None = None, **kwargs: Any):
        """Stand in for agent._build_model, keeping its callback contract."""
        callbacks = [UsageRecordingHandler(thread_id)] if thread_id else []
        return _Recorder(callbacks=callbacks)

    monkeypatch.setattr(agent_mod, "_build_model", _fake_build_model)

    def _build(thread_id: str):
        graph, _backend = agent_mod.create_orchestrator(thread_id)
        return graph

    return _build


async def _two_turns(graph: Any, thread_id: str) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    await graph.ainvoke({"messages": [HumanMessage("first")]}, config=config)
    await graph.ainvoke({"messages": [HumanMessage("second")]}, config=config)


def test_prefix_is_identical_across_turns(built_agent) -> None:
    """Turn 2 must reuse turn 1's exact bytes, or the cache can never hit."""
    graph = built_agent("cache-prefix-turns")
    asyncio.run(_two_turns(graph, "cache-prefix-turns"))

    assert len(RECORDED) >= 2
    first, second = RECORDED[0], RECORDED[1]
    assert _prefix(first) == _prefix(second)

    # The earlier messages must also be untouched: the provider matches the
    # whole prefix, not just the system prompt.
    n = min(len(first["messages"]), len(second["messages"]))
    assert n >= 2
    for i in range(n):
        assert _body(first["messages"][i]) == _body(second["messages"][i])


def test_prefix_is_identical_across_agent_builds(built_agent) -> None:
    """A rebuilt orchestrator (new chat session, settings change) must match.

    Sessions rebuild their agent freely; if the build were not deterministic,
    every new session would start from a cold cache.
    """

    async def _build_and_ask(graph: Any) -> None:
        await graph.ainvoke(
            {"messages": [HumanMessage("hi")]},
            config={"configurable": {"thread_id": "cache-prefix-builds"}},
        )

    graph_a = built_agent("cache-prefix-builds")
    asyncio.run(_build_and_ask(graph_a))
    graph_b = built_agent("cache-prefix-builds")
    asyncio.run(_build_and_ask(graph_b))

    assert len(RECORDED) >= 2
    assert _prefix(RECORDED[0]) == _prefix(RECORDED[1])



def test_usage_handler_fires_inside_the_graph(built_agent) -> None:
    """A model-level callback must survive deepagents' graph and tool binding.

    This is the wiring the ledger depends on: the handler is attached to the
    model instance, and deepagents binds tools and runs that instance inside a
    compiled graph. If the binding dropped the callback, every usage number
    would silently read zero — the exact failure mode this feature exists to
    make visible.
    """
    from sdlc.services.usage import UsageLedger

    graph = built_agent("cache-usage-wiring")
    asyncio.run(_two_turns(graph, "cache-usage-wiring"))

    snap = UsageLedger.snapshot("cache-usage-wiring")
    assert snap["calls"] >= 2
    assert snap["input_tokens"] == 4000 * snap["calls"]
    assert snap["cached_tokens"] == 3500 * snap["calls"]
    assert 0.8 < snap["cache_hit_ratio"] < 0.9

def test_cache_key_is_sent_only_where_it_is_documented(monkeypatch) -> None:
    """auto = OpenAI only; on = always; off = never.

    An undocumented body field sent to a strict OpenAI-compatible gateway is a
    400 on every request, so the default must not guess.
    """
    from sdlc.services import agent as agent_mod

    openai_settings = {"base_url": "https://api.openai.com/v1"}
    gateway_settings = {"base_url": "https://hub.nhr.fau.de/api/llmgw/v1"}

    monkeypatch.setattr(agent_mod, "PROMPT_CACHE_KEY", "auto")
    assert agent_mod._prompt_cache_key(openai_settings, "t1") == "t1"
    assert agent_mod._prompt_cache_key(gateway_settings, "t1") is None
    assert agent_mod._prompt_cache_key(openai_settings, None) is None

    monkeypatch.setattr(agent_mod, "PROMPT_CACHE_KEY", "on")
    assert agent_mod._prompt_cache_key(gateway_settings, "t1") == "t1"

    monkeypatch.setattr(agent_mod, "PROMPT_CACHE_KEY", "off")
    assert agent_mod._prompt_cache_key(openai_settings, "t1") is None


def test_model_carries_cache_key_and_usage_handler(monkeypatch) -> None:
    """The cache key and the ledger must actually reach the model instance."""
    from sdlc.services import agent as agent_mod
    from sdlc.services import model_settings
    from sdlc.services.usage import UsageRecordingHandler

    monkeypatch.setattr(agent_mod, "PROMPT_CACHE_KEY", "on")
    monkeypatch.setattr(
        model_settings,
        "get_effective_settings",
        lambda: {
            "model_provider": "openai",
            "agent_model": "cache-model",
            "base_url": "http://localhost:1/v1",
            "api_key": "x",
            "reasoning_effort": "",
        },
    )

    model = agent_mod._build_model("thread-with-cache")
    assert model.extra_body == {"prompt_cache_key": "thread-with-cache"}
    assert any(isinstance(cb, UsageRecordingHandler) for cb in (model.callbacks or []))

    # No thread id (e.g. a one-shot compaction call) means no key and no ledger.
    bare = agent_mod._build_model()
    assert not bare.extra_body
    assert not bare.callbacks
