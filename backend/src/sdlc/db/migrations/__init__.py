"""Alembic migrations for the SDLC harness DB.

Revisions live in ``versions/`` and are run automatically on backend
startup via ``sdlc.db.engine.init_db``. To create a new revision::

    cd backend
    set DATABASE_URL=postgresql+asyncpg://harness:harness@localhost:5432/harness
    alembic -c src/sdlc/db/alembic.ini revision --autogenerate -m "describe change"
"""
