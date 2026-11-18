"""End-to-end HITL approval tests against a real deepagents agent.

Uses a fake tool-calling model + in-memory checkpointer (no LLM, no Docker) to
exercise the full approve / reject / edit / shell-guard paths through
``create_deep_agent(interrupt_on=..., middleware=[ShellGuardMiddleware()])`` and
the runner's interrupt detection (``_pending_interrupts``) + ``Command`` resume.

Run: ``uv run pytest tests/test_hitl_integration.py``.
"""

from __future__ import annotations

import os

# Disable LangSmith tracing so the test doesn't hit the network / rate limits.
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

import asyncio

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

try:
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    from deepagents import create_deep_agent

    from sdlc.services.hitl import INTERRUPT_ON, ShellGuardMiddleware
    from sdlc.api.app import _pending_interrupts

    _DEPS_OK = True
except Exception:  # pragma: no cover - environment without the agent stack
    _DEPS_OK = False

pytestmark = pytest.mark.skipif(not _DEPS_OK, reason="agent stack unavailable")


class _FakeToolModel(FakeMessagesListChatModel):
    """Returns scripted messages (preserving tool_calls); tolerates bind_tools."""

    def bind_tools(self, tools, **kwargs):  # noqa: ANN001, D102
        return self


def _agent_with(msgs):
    return create_deep_agent(
        model=_FakeToolModel(responses=msgs),
        interrupt_on=INTERRUPT_ON,
        middleware=[ShellGuardMiddleware()],
        checkpointer=InMemorySaver(),
    )


def _tool_msgs(state, name):
    return [
        m for m in state.values.get("messages", [])
        if isinstance(m, ToolMessage) and getattr(m, "name", "") == name
    ]


async def _drain(agent, inp, cfg):
    async for _ in agent.astream(inp, cfg, stream_mode="messages"):
        pass


_WRITE = AIMessage(content="", tool_calls=[
    {"name": "write_file", "args": {"file_path": "/note.md", "content": "hello"},
     "id": "c1", "type": "tool_call"}])
_DONE = AIMessage(content="Done.")


async def _approve():
    agent = _agent_with([_WRITE, _DONE])
    cfg = {"configurable": {"thread_id": "approve"}}
    await _drain(agent, {"messages": [HumanMessage(content="go")]}, cfg)
    st = await agent.aget_state(cfg)
    ints = _pending_interrupts(st)
    assert ints and ints[0].value["action_requests"][0]["name"] == "write_file"
    assert not _tool_msgs(st, "write_file")  # gated — not yet executed
    await _drain(agent, Command(resume={"decisions": [{"type": "approve"}]}), cfg)
    st2 = await agent.aget_state(cfg)
    assert not _pending_interrupts(st2)
    tms = _tool_msgs(st2, "write_file")
    assert tms and tms[0].status != "error"


async def _reject():
    agent = _agent_with([_WRITE, _DONE])
    cfg = {"configurable": {"thread_id": "reject"}}
    await _drain(agent, {"messages": [HumanMessage(content="go")]}, cfg)
    await _drain(agent, Command(resume={"decisions": [{"type": "reject", "message": "no thanks"}]}), cfg)
    st = await agent.aget_state(cfg)
    tms = _tool_msgs(st, "write_file")
    assert tms and tms[0].status == "error" and "no thanks" in str(tms[0].content)


async def _edit():
    agent = _agent_with([_WRITE, _DONE])
    cfg = {"configurable": {"thread_id": "edit"}}
    await _drain(agent, {"messages": [HumanMessage(content="go")]}, cfg)
    edited = {"file_path": "/renamed.md", "content": "EDITED"}
    await _drain(agent, Command(resume={"decisions": [
        {"type": "edit", "edited_action": {"name": "write_file", "args": edited}}]}), cfg)
    st = await agent.aget_state(cfg)
    tms = _tool_msgs(st, "write_file")
    assert tms and tms[0].status != "error"


async def _shell_guard():
    bad = AIMessage(content="", tool_calls=[
        {"name": "execute", "args": {"command": "rm -rf /"}, "id": "s1", "type": "tool_call"}])
    agent = _agent_with([bad, _DONE])
    cfg = {"configurable": {"thread_id": "shell"}}
    await _drain(agent, {"messages": [HumanMessage(content="clean up")]}, cfg)
    st = await agent.aget_state(cfg)
    assert not _pending_interrupts(st)  # shell never pauses for approval
    tms = _tool_msgs(st, "execute")
    assert tms and tms[0].status == "error" and "BLOCKED" in str(tms[0].content)


def test_approve_path():
    asyncio.run(_approve())


def test_reject_path():
    asyncio.run(_reject())


def test_edit_path():
    asyncio.run(_edit())


def test_shell_guard_blocks_destructive():
    asyncio.run(_shell_guard())
