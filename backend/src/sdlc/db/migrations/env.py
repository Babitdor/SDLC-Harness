"""Alembic environment.

Wraps the async SQLAlchemy engine so the runtime ``init_db()`` path
(which calls ``alembic.command.upgrade``) doesn't need a separate
sync driver. Falls back to ``sync`` mode if there's no event loop —
that's what plain ``alembic`` CLI calls hit.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine, async_engine_from_config

# Import the metadata that ``autogenerate`` compares the live DB against.
# ``import sdlc.db`` pulls in the engine module which exposes Base, but
# models must be imported explicitly so their tables are registered on
# Base.metadata before this script runs.
from sdlc.db import Base  # noqa: F401
from sdlc.db import models  # noqa: F401  - registers tables

config = context.config

if config.config_file_name is not None:
    # disable_existing_loggers defaults to True, which silently kills every
    # logger that already exists — including uvicorn.error, so unhandled
    # request exceptions never printed their traceback.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _get_url() -> str:
    """Resolve the URL from the alembic Config (set at runtime by
    ``sdlc.db.engine._alembic_config()``)."""
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        msg = "sqlalchemy.url is not set in the Alembic config"
        raise RuntimeError(msg)
    return url


def run_migrations_offline() -> None:
    """Render SQL to stdout — used by ``alembic upgrade --sql``."""
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Apply migrations using an async engine (matches the runtime stack)."""
    connectable = create_async_engine(_get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Online migration entrypoint.

    If we're inside an event loop (the FastAPI startup path),
    ``asyncio.run`` would explode — fall back to running the coroutine on
    the existing loop. The plain ``alembic`` CLI invocation hits the
    no-loop branch.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # ``alembic.command.upgrade`` already runs inside a worker
            # thread (see sdlc.db.engine.init_db) — no loop here.
            loop.run_until_complete(run_async_migrations())
            return
    except RuntimeError:
        pass
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
