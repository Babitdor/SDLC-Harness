"""ORM models for conversations + messages.

A *conversation* corresponds 1:1 with what the frontend used to call a
"thread" (and what the LangGraph checkpointer keys by ``thread_id``). We
keep that vocabulary for the public API so frontend code doesn't have to
change concept names, but the DB table is ``conversation`` to match
standard SQL naming.

A *message* is one row per chat turn — user, assistant, or system —
including the rich payload (tool calls + attachments) the frontend used
to store as nested JSON in localStorage. Both are stored as ``JSONB`` so
we can keep them as arrays without flattening.

Ownership: a conversation belongs to one ``app_user`` row and a session is
an opaque token in ``user_session``. ``Conversation.user_id`` is nullable
because the column arrived after the first conversations existed — a NULL row
is a pre-auth legacy conversation, filtered out of every query by design, so
"invisible until claimed" needs no extra table state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .engine import Base


def _utc_now() -> datetime:
    """Server-side fallback for created_at / updated_at when the DB
    default isn't applied (e.g. ORM-side construction without flush)."""
    return datetime.now(timezone.utc)


class Conversation(Base):
    """One chat thread.

    The id doubles as the LangGraph thread_id and the Docker container
    suffix (``harness-<id>``), so once a conversation row exists, all
    downstream systems can reference it by that id alone.
    """

    __tablename__ = "conversation"

    # Generated client-side (frontend used to do ``crypto.randomUUID()``
    # and the deterministic container naming depends on the same id), so
    # store as a plain string column rather than a server-side ``uuid``
    # type. Backwards compatible if we later promote to UUID.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="", server_default="")
    project_id: Mapped[str] = mapped_column(
        String(64), default="default", server_default="default", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        onupdate=_utc_now,
        nullable=False,
        index=True,
    )

    # Owning account. NULL = a pre-auth legacy row: still in the table, but
    # unreachable, because every read path filters on user_id. ``SET NULL``
    # rather than CASCADE on purpose — deleting an account must not quietly
    # delete other people's audit trail.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        # The sidebar query — "my conversations, newest first" — in one index.
        Index("ix_conversation_user_updated", "user_id", "updated_at"),
    )

    # cascade so deleting a conversation drops its messages — the
    # frontend's deleteConversation flow already implies the messages go
    # with it.
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:  # noqa: D401 — short repr is plenty
        return f"<Conversation id={self.id!r} title={self.title!r}>"


class Message(Base):
    """One chat message inside a conversation.

    ``role`` is the LangChain message type — ``"human"``, ``"ai"``,
    ``"system"`` — matching how the frontend already keys its render. We
    keep ``content`` as plain text for the common case but allow rich
    payloads via the JSONB sidecar columns (``tool_calls``, ``attachments``).
    """

    __tablename__ = "message"

    # Surrogate integer PK; client-supplied UUIDs aren't useful for
    # ordering and ints are tighter for the FK from conversation.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", server_default="")
    agent_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Rich tool-call envelope from the SSE stream. Stored as JSONB so
    # Postgres can index/query inside it later if we want analytics.
    tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    # File chips the user attached to the bubble.
    attachments: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    # Agent thinking/reasoning process (native model reasoning or planning narration).
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    __table_args__ = (
        # Single composite index for the dominant access pattern:
        # "give me all messages for conversation X ordered by time".
        Index("ix_message_conversation_created", "conversation_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role!r} convo={self.conversation_id}>"


class AppUser(Base):
    """One account.

    Email is stored as typed (so it can be shown back) but its uniqueness is
    case-insensitive: that lives in a functional index on ``lower(email)``
    created by migration 0003. A plain UNIQUE constraint would happily accept
    ``A@x.com`` and ``a@x.com`` as two accounts, and the login form would
    then have to guess which one was meant.
    """

    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    # Opaque "scrypt$n$r$p$salt$hash" string — see sdlc.core.security.
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(
        String(120), default="", server_default="", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AppUser id={self.id} email={self.email!r}>"


class UserSession(Base):
    """One logged-in browser.

    The primary key is the SHA-256 of the cookie value, never the cookie
    value: a leaked database dump then cannot be replayed as a login, and the
    row is still an O(1) lookup on the way in.
    """

    __tablename__ = "user_session"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    # Indexed: expiry sweeps and "is this token still valid" both scan it.
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    # Refreshed lazily (at most hourly) so a fast chat stream does not turn
    # into one UPDATE per request.
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        server_default=func.now(),
        nullable=False,
    )
    user_agent: Mapped[str] = mapped_column(
        String(200), default="", server_default="", nullable=False
    )
    ip: Mapped[str] = mapped_column(String(64), default="", server_default="", nullable=False)

    user: Mapped[AppUser] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        return f"<UserSession user_id={self.user_id} expires_at={self.expires_at}>"
