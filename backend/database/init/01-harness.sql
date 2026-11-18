-- ── Postgres init script ──────────────────────────────────────────────
--
-- Runs ONCE on first start of the sdlc-harness-postgres container (after the
-- data volume is initialised). Postgres only invokes
-- /docker-entrypoint-initdb.d on a freshly created data directory — if
-- you change this file, wipe the volume (`docker compose down -v`)
-- before bringing the stack back up.
--
-- This file is intentionally limited to *database creation* only. Table
-- schemas are owned by Alembic (`backend/src/mbse/db/migrations/`).
-- Running schema DDL here too races the backend's startup
-- `alembic upgrade head` and leaves a mixed-shape database — the early
-- draft of this file did exactly that and conflicted with the SQLAlchemy
-- models (different table names and columns).
--
-- Databases created:
--   harness — conversations + messages for the backend (Alembic-managed)

CREATE DATABASE harness OWNER postgres;
