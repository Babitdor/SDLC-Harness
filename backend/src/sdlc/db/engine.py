"""Async engine + session factory + Alembic migration runner.

We use SQLAlchemy 2.0's async engine over asyncpg. The url is read once
from ``config.DATABASE_URL`` and normalised so the standard
``postgresql://`` form also works (we rewrite it to
``postgresql+asyncpg://``).

``init_db()`` is awaited from the FastAPI lifespan startup. It:
  1. Opens the engine.
  2. Runs ``alembic upgrade head`` programmatically so the schema is
     always at the head revision before any endpoint is served.

``close_db()`` disposes the engine at shutdown.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from sdlc.core.config import DATABASE_URL

logger = logging.getLogger(__name__)


def _normalise_url(url: str) -> str:
    """Force the async-driver URL form.

    ``DATABASE_URL=postgresql://...`` is the conventional form in
    deployment configs, but SQLAlchemy's async engine needs an explicit
    ``+asyncpg``. Rewriting here lets ops use either form.
    """
    if url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


_normalised_url = _normalise_url(DATABASE_URL)


engine: AsyncEngine = create_async_engine(
    _normalised_url,
    # Modest pool — backend serves a small number of concurrent users in
    # this single-host phase. Tune up later if needed.
    pool_size=10,
    max_overflow=5,
    # Recycle stale connections; Postgres servers will close idle
    # connections after a while and the recycle hint avoids surprise
    # disconnects mid-request.
    pool_recycle=300,
    # echo=True is useful while bringing up the schema; leave off in prod.
    echo=False,
)

_SessionFactory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Declarative base every ORM model inherits from."""


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` with commit / rollback / close handling.

    Usage in an endpoint::

        async with session_scope() as session:
            session.add(obj)
            # commit happens on context exit
    """
    session = _SessionFactory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ── Migration runner ────────────────────────────────────────────────────


def _alembic_config() -> "object":
    """Build an Alembic ``Config`` pointing at our migrations directory.

    Imported lazily so the dependency is only resolved when init_db()
    actually runs — keeps unit tests that mock the db layer fast.
    """
    from alembic.config import Config

    here = Path(__file__).resolve().parent
    alembic_ini = here / "alembic.ini"
    if not alembic_ini.exists():
        msg = f"alembic.ini not found at {alembic_ini}"
        raise RuntimeError(msg)
    cfg = Config(str(alembic_ini))
    # Point script_location at the migrations dir relative to the ini's
    # parent (sdlc/db/), not the current working directory.
    cfg.set_main_option("script_location", str(here / "migrations"))
    # Override the URL — alembic.ini ships with a placeholder; the real
    # URL lives in DATABASE_URL.
    cfg.set_main_option("sqlalchemy.url", _normalised_url)
    return cfg


async def init_db() -> None:
    """Run Alembic migrations to head and verify connectivity.

    Migrations execute synchronously (alembic's API is sync-only), so we
    run them in a worker thread to keep the event loop unblocked. After
    migration we issue a trivial ``SELECT 1`` to confirm the engine can
    actually reach the database — failing fast at startup is much nicer
    than discovering it on the first request.

    First action is ``await engine.dispose()`` — when running under
    gunicorn the master imports this module (creating the engine + its
    connection pool) BEFORE forking workers; each forked worker
    inherits the parent's open sockets, and multiple processes
    multiplexing the same TCP connection deadlocks the asyncpg driver.
    Disposing on each worker's startup drops the inherited pool so the
    fresh connections opened from here on belong to this process alone.
    Safe to call when there's nothing to dispose (no-op).
    """
    import asyncio

    from alembic import command
    from sqlalchemy import text

    # Drop any connections that survived the fork from the gunicorn
    # master — see docstring above. Without this, the lifespan hangs at
    # `engine.connect()` and never reaches the rest of FastAPI's
    # startup, so the in-memory checkpointer + orchestrator factories
    # are never initialised. Endpoints then return 500 with no usable
    # traceback because uvicorn falls back to lifespan="off".
    await engine.dispose()

    cfg = _alembic_config()

    def _upgrade() -> None:
        command.upgrade(cfg, "head")

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _upgrade)
    except Exception:
        logger.exception("Alembic migration failed during init_db()")
        raise

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database ready (url=%s)", _redact_url(_normalised_url))


async def close_db() -> None:
    """Dispose the engine on shutdown."""
    await engine.dispose()
    logger.info("Database engine disposed")


def _redact_url(url: str) -> str:
    """Strip credentials from a DB URL for log-safe display."""
    if "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    _creds, host = rest.split("@", 1)
    return f"{scheme}://***@{host}"
