"""DB-backed conversation + message store.

Thin async CRUD layer over the SQLAlchemy models in ``sdlc.db.models``.
Endpoints in ``api/app.py`` import these helpers rather than doing
SQLAlchemy work directly — keeps the route handlers focused on
serialisation + HTTP semantics.

All functions accept an explicit ``AsyncSession`` so callers can compose
multiple operations in one transaction if needed. The endpoints use
``session_scope()`` as the unit of work.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sdlc.db.models import Conversation, Message

logger = logging.getLogger(__name__)


def _iso(dt: datetime) -> str:
    """Render a timezone-aware datetime as ISO 8601 UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _conversation_to_summary(c: Conversation, message_count: int) -> dict[str, Any]:
    return {
        "id": c.id,
        "title": c.title or "",
        "project_id": c.project_id,
        "created_at": _iso(c.created_at),
        "updated_at": _iso(c.updated_at),
        "message_count": message_count,
    }


def _message_to_dict(m: Message) -> dict[str, Any]:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "role": m.role,
        "content": m.content or "",
        "agent_name": m.agent_name,
        "trace_url": m.trace_url,
        "tool_calls": m.tool_calls,
        "attachments": m.attachments,
        "reasoning": m.reasoning,
        "created_at": _iso(m.created_at),
    }


# ── Conversations ───────────────────────────────────────────────────────


async def list_conversations(
    session: AsyncSession, user_id: int
) -> list[dict[str, Any]]:
    """Return one user's conversations, newest first.

    The ``user_id`` filter is also what hides pre-auth rows: their
    ``user_id`` is NULL, and NULL never equals an account id.
    """
    stmt = (
        select(Conversation, func.count(Message.id).label("msg_count"))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user_id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
    )
    rows = (await session.execute(stmt)).all()
    return [_conversation_to_summary(c, n) for c, n in rows]


async def get_conversation(session: AsyncSession, conversation_id: str) -> Conversation | None:
    return await session.get(Conversation, conversation_id)


async def create_conversation(
    session: AsyncSession,
    *,
    conversation_id: str,
    user_id: int,
    title: str = "",
    project_id: str = "default",
) -> Conversation:
    """Insert a new conversation row, raising if the id already exists.

    Frontend code is expected to generate the id via ``crypto.randomUUID``
    so collisions are astronomically rare; the IntegrityError path exists
    to surface them clearly anyway.
    """
    convo = Conversation(
        id=conversation_id, title=title, project_id=project_id, user_id=user_id
    )
    session.add(convo)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        msg = f"Conversation with id {conversation_id!r} already exists"
        raise ValueError(msg) from exc
    return convo


async def update_conversation(
    session: AsyncSession,
    conversation_id: str,
    *,
    title: str | None = None,
) -> Conversation | None:
    convo = await get_conversation(session, conversation_id)
    if convo is None:
        return None
    if title is not None:
        convo.title = title
    convo.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return convo


async def delete_conversation(session: AsyncSession, conversation_id: str) -> bool:
    """Drop a conversation (cascade deletes its messages)."""
    convo = await get_conversation(session, conversation_id)
    if convo is None:
        return False
    await session.delete(convo)
    await session.flush()
    return True


def conversation_to_summary_dict(c: Conversation, message_count: int) -> dict[str, Any]:
    """Public helper used by the create endpoint (returns the freshly
    inserted row in list-view shape)."""
    return _conversation_to_summary(c, message_count)


# ── Messages ────────────────────────────────────────────────────────────


async def list_messages(
    session: AsyncSession,
    conversation_id: str,
) -> list[dict[str, Any]] | None:
    """Return the full message history of a conversation, ordered chronologically.

    Returns ``None`` if the conversation doesn't exist (so the endpoint
    can 404 cleanly).
    """
    convo = await get_conversation(session, conversation_id)
    if convo is None:
        return None

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_message_to_dict(m) for m in rows]


async def append_message(
    session: AsyncSession,
    conversation_id: str,
    *,
    role: str,
    content: str = "",
    agent_name: str | None = None,
    trace_url: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    reasoning: str | None = None,
) -> dict[str, Any] | None:
    """Append a message and bump the conversation's ``updated_at``.

    Returns the inserted row serialised, or ``None`` if the conversation
    doesn't exist.
    """
    convo = await get_conversation(session, conversation_id)
    if convo is None:
        return None

    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        agent_name=agent_name,
        trace_url=trace_url,
        tool_calls=tool_calls,
        attachments=attachments,
        reasoning=reasoning,
    )
    session.add(msg)
    convo.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return _message_to_dict(msg)


async def replace_messages(
    session: AsyncSession,
    conversation_id: str,
    messages: list[dict[str, Any]],
) -> bool:
    """Bulk replace a conversation's history.

    Used by the frontend's localStorage migration path — on first load
    after the database goes live, the client uploads its existing
    per-thread messages so nothing is lost. Truncates the table and
    re-inserts atomically.
    """
    convo = await get_conversation(session, conversation_id)
    if convo is None:
        return False

    # Wipe then re-insert. cascade="all, delete-orphan" on the relationship
    # makes a plain ``DELETE WHERE conversation_id = ...`` the right call —
    # we don't need to issue per-row deletes.
    from sqlalchemy import delete

    await session.execute(delete(Message).where(Message.conversation_id == conversation_id))

    for m in messages:
        session.add(
            Message(
                conversation_id=conversation_id,
                role=m.get("role", "unknown"),
                content=m.get("content", "") or "",
                agent_name=m.get("agent_name"),
                trace_url=m.get("trace_url"),
                tool_calls=m.get("tool_calls"),
                attachments=m.get("attachments"),
                reasoning=m.get("reasoning"),
            )
        )
    convo.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return True
