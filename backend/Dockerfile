# syntax=docker/dockerfile:1.7
# ── SDLC Harness Backend ────────────────────────────────────────────────
#
# Multi-stage build: install deps in a build stage, then copy to a slim
# runtime image. The runtime image mounts the host Docker socket so the
# backend can spawn per-chat sandbox containers as siblings.
#
# The `# syntax=` line above enables BuildKit cache mounts (used below to
# keep the pip download cache across rebuilds — first build is full
# resolution; subsequent dep-only changes reuse cached wheels).

# ── Build stage ──────────────────────────────────────────────────────
# Dependencies are resolved from uv.lock (the same lockfile local dev
# uses) — NOT re-resolved from pyproject.toml. `uv export --frozen`
# turns the lock into a fully pinned requirements.txt; the deepagents
# 0.7.8-vs-0.6.3 drift incident is exactly what this prevents.
#
# Layer order: lock files first → dep wheels (cached until the lock
# changes) → THEN src/ for the small project wheel. Editing src/ no
# longer re-builds 460 dependency wheels.
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir setuptools wheel uv

# uv.lock copied with pyproject/README: the export below needs both, and
# this COPY is the cache boundary for everything downstream.
COPY pyproject.toml README.md uv.lock ./

# Freeze the locked dependency set (no project entry — the project wheel
# is built separately below so source edits don't touch this layer).
RUN uv export --frozen --no-dev --no-hashes --no-emit-project \
        -o requirements.txt

# Dep wheels from the pinned requirements — no resolution, fully cached
# until uv.lock changes. The pip cache mount makes a lock bump only
# re-download the changed packages.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir=/wheels -r requirements.txt

# Project wheel — setuptools needs the README (pyproject's
# `readme = "README.md"`) and src/ for its egg_info step. `--no-deps`
# keeps this layer fast: deps are already built above.
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-deps --wheel-dir=/wheels .

# ── Runtime stage ────────────────────────────────────────────────────
FROM python:3.12-slim

# ── Headless draw.io Desktop (PNG/SVG/PDF export) ────────────────────
# draw.io Desktop is an Electron app, so CLI export needs a display.
# We install the .deb (apt resolves its GTK/NSS/GBM/ALSA deps) plus
# Xvfb; DrawioExportDiagram wraps the binary in `xvfb-run` at call time.
# Pinned + bumpable: `--build-arg DRAWIO_VERSION=<x.y.z>`. This layer is
# heavy (~Electron), so it sits above the app-source COPY to stay cached
# across code edits.
ARG DRAWIO_VERSION=30.0.4
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget ca-certificates xvfb xauth libasound2t64 && \
    wget --tries=5 --timeout=60 --retry-connrefused --waitretry=5 -q \
         "https://github.com/jgraph/drawio-desktop/releases/download/v${DRAWIO_VERSION}/drawio-amd64-${DRAWIO_VERSION}.deb" \
         -O /tmp/drawio.deb && \
    apt-get install -y --no-install-recommends /tmp/drawio.deb && \
    rm -f /tmp/drawio.deb && \
    apt-get purge -y wget && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
# Tell the CLI detector exactly where the binary is (skips the path scan).
ENV DRAWIO_CLI_PATH=/usr/bin/drawio

WORKDIR /app

# ── Playwright headless Chromium (HTML diagram validation) ───────────
# Sits BEFORE the dependency install so dependency changes never
# re-download the browser payload. `--only-shell` installs just the
# chromium-headless-shell build (~262 MB instead of ~651 MB): the only
# Playwright consumer (SankeyGeneratorTool) always launches
# headless=True with no `channel:` override, which Playwright 1.49+
# serves from the headless shell. Bump PLAYWRIGHT_VERSION together with
# the version pinned in uv.lock (playwright==1.60.0).
ARG PLAYWRIGHT_VERSION=1.60.0
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/local/share/ms-playwright
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    --mount=type=cache,target=/root/.cache/ms-playwright,sharing=locked,uid=0,gid=0 \
    pip install --no-cache-dir "playwright==${PLAYWRIGHT_VERSION}" && \
    playwright install --with-deps --only-shell chromium

# Install the locked dependency wheels + project wheel from the builder
# via a bind-mount — the wheels never enter an image layer at all, so
# the old 213 MB orphaned /wheels COPY layer disappears entirely.
# gunicorn ships via the lock (pyproject dependency) — no extra install.
RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --no-cache-dir /wheels/*.whl

# uv in the RUNTIME image, not just the builder: Python MCP servers are
# launched as `uvx <package>` subprocesses by services/mcp.py (the "fetch"
# preset). Without uvx, every stdio preset fails at connect with a bare
# "no such file" and the panel looks broken. ~10 MB for the capability.
RUN pip install --no-cache-dir uv

# Application source — copied AFTER deps so editing code doesn't
# invalidate the wheel layer.
COPY src/ ./src/
COPY main.py .

# ── Non-root user ────────────────────────────────────────────────────
# Create a dedicated `sdlc` account (uid/gid 1001) and a `docker` group so
# the user can read the mounted Docker socket. We prefer GID 999 (the common
# host default) but fall back to an auto-assigned GID — the headless-drawio
# apt layer above pulls in packages (dbus, x11) that may already claim 999.
# Either way, socket access at runtime comes from `group_add: ["0"]` in
# compose (numeric `user:` skips /etc/group supplementary groups), so the
# exact GID here is best-effort only — see docker-compose.yml.
RUN ( getent group docker >/dev/null || groupadd --system --gid 999 docker \
      || groupadd --system docker ) && \
    groupadd --system --gid 1001 sdlc && \
    useradd --system --uid 1001 --gid sdlc --groups docker \
            --no-create-home --home-dir /app --shell /usr/sbin/nologin sdlc && \
    mkdir -p /app/data /app/uploads && \
    # `.keep` files force Docker to seed named volumes from the image's
    # version of these directories on first mount, which carries over
    # the chown below. Without seed content, the volume is created empty
    # and owned by root — sqlite then can't write its checkpoint file.
    touch /app/data/.keep /app/uploads/.keep && \
    chown -R sdlc:sdlc /app

USER 1001:1001

EXPOSE 8000

# Production default: gunicorn + a SINGLE uvicorn worker.
#
# This MUST stay at -w 1. The app coordinates chat runs through in-memory,
# per-process state — the detached agent-runner tasks (`_active_runs`), the
# live SSE event buffers + subscriber queues and pending human-approval
# futures (`_run_contexts`), the session/agent cache, and the artifact cache.
# None of that is shared across processes (an asyncio.Future can't cross a
# fork), so with multiple workers the SSE stream sticks to one worker while a
# follow-up request (POST /chat/{id}/decision, GET /chat/resume) round-robins
# to another that has no record of the run -> 404. A single async UvicornWorker
# handles this I/O-bound, streaming workload with plenty of concurrency.
#
# Override at the compose level with `command: python main.py` for hot-reload dev.
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "300", "--bind", "0.0.0.0:8000", "sdlc.api.app:app"]
