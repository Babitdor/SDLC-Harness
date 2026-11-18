"""Async Postgres persistence for conversations + messages.

Stands in for the frontend's localStorage so chats survive across
machines/browsers. The agent's own LangGraph checkpoints remain in
SQLite (see CHECKPOINT_DB_PATH in core.config) until a later phase
migrates them too.

Public surface:
    Base          — declarative base every model inherits from
    engine        — singleton async engine
    session_scope — async context manager that yields an AsyncSession
                    and handles commit / rollback / close.

The first call to ``init_db()`` runs Alembic migrations (so the
deployment doesn't need a manual ``alembic upgrade head`` step).
``close_db()`` disposes the engine cleanly on shutdown.
"""

from __future__ import annotations

from .engine import Base, close_db, engine, init_db, session_scope

__all__ = ["Base", "close_db", "engine", "init_db", "session_scope"]
