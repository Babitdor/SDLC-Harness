"""SDLC Harness — run the orchestrator server.

Usage:
    python main.py                      # single-process uvicorn (dev)
    python main.py --reload             # auto-reload on file changes (dev)
    python main.py --port 8080          # custom port
    python main.py --workers 4          # multi-process via uvicorn workers
    python main.py --prod               # gunicorn + uvicorn workers (production)

Or via the installed script:
    serve
    serve --reload
"""

from __future__ import annotations

import sys
from sdlc.api.app import main

if __name__ == "__main__":
    from sdlc.core.config import HOST, PORT

    reload = "--reload" in sys.argv
    prod = "--prod" in sys.argv

    port = PORT
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
        if arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])

    workers = None
    for i, arg in enumerate(sys.argv):
        if arg in ("--workers", "-w") and i + 1 < len(sys.argv):
            workers = int(sys.argv[i + 1])
        if arg.startswith("--workers="):
            workers = int(arg.split("=", 1)[1])

    if prod:
        # ── Production: gunicorn + uvicorn workers ───────────────────
        # Multiple processes isolate the SSE stream from REST requests.
        # If one worker's event loop is blocked by a long Docker exec,
        # the other workers still handle artifact reads and health checks.
        # Default: 4 workers (2× CPU cores on a typical dev machine).
        gunicorn_workers = workers or 4

        bind = f"{HOST}:{port}"
        worker_class = "uvicorn.workers.UvicornWorker"

        import gunicorn.app.base

        class StandaloneApp(gunicorn.app.base.BaseApplication):
            def __init__(self):
                self.options = {
                    "bind": bind,
                    "workers": gunicorn_workers,
                    "worker_class": worker_class,
                    "timeout": 300,  # long timeout for agent streaming
                    "graceful_timeout": 30,
                }
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    if key in self.cfg.settings and value is not None:
                        self.cfg.set(key, value)

            def load(self):
                from sdlc.api.app import app
                return app

        StandaloneApp().run()

    elif workers:
        # ── Multi-worker uvicorn (without gunicorn) ──────────────────
        import uvicorn
        uvicorn.run(
            "sdlc.api.app:app",
            host=HOST,
            port=port,
            reload=reload,
            workers=workers,
        )
    else:
        # ── Dev / single-process ─────────────────────────────────────
        import uvicorn
        uvicorn.run(
            "sdlc.api.app:app",
            host=HOST,
            port=port,
            reload=reload,
        )
