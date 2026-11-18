"""Docker-based sandbox backend for Deep Agents.

Uses a Docker container as an isolated execution environment. All file
operations and shell commands run inside the container, providing process
and filesystem isolation from the host.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import shlex
import subprocess
import tarfile
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from deepagents.backends.protocol import (
    ExecuteResponse,
    FileDownloadResponse,
    FileUploadResponse,
)
from deepagents.backends.sandbox import BaseSandbox

logger = logging.getLogger(__name__)

__all__ = ["DockerBackend", "ensure_image", "gc_orphan_containers"]

# ── Sandbox isolation floor ────────────────────────────────────────────
# Each container is single-tenant and runs agent-authored shell commands that
# are ultimately steered by untrusted uploaded documents. The defaults below
# are the floor, not a suggestion: all capabilities are dropped, privilege
# escalation is blocked, process count / memory / CPU are bounded, and the
# network is off — nothing inside the sandbox needs egress, because model and
# tool traffic originates in the backend process, never in the container.
SANDBOX_LABEL = "harness.sandbox"
THREAD_LABEL = "harness.thread"

# uid:gid every agent-facing exec runs as. The container starts as root only
# long enough to chown the workdir, then each `docker exec` drops to this
# user — the agent never gets a root shell inside its own sandbox. Files
# written by the daemon (put_archive uploads) are re-chowned back to it.
DEFAULT_SANDBOX_USER = "1000:1000"

# Commands are wrapped in coreutils `timeout` (see _exec_cmd) so a hung
# command cannot pin an executor thread for the life of the process.
_TIMEOUT_KILL_GRACE_S = 5


def ensure_image(image: str) -> bool:
    """Make sure *image* is present locally, pulling it when it is not.

    Runs from the startup warm-up task so the first chat does not pay for a
    multi-hundred-megabyte pull inside its `docker run`. Never raises: a warm
    cache is an optimisation, and a genuinely missing image is reported by the
    first container creation with a better message than a boot failure.
    """
    try:
        import docker as _docker

        # A pull streams for minutes; the 5s used elsewhere would abort it.
        client = _docker.from_env(timeout=60)
    except Exception as exc:  # noqa: BLE001 — warm-up must never break boot
        logger.warning("Sandbox image warm-up skipped: %s", exc)
        return False
    try:
        try:
            client.images.get(image)
            logger.info("Sandbox image %s already present", image)
            return True
        except Exception:
            logger.info("Pulling sandbox image %s (first run only)", image)
            client.images.pull(image)
            logger.info("Sandbox image %s ready", image)
            return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not pull sandbox image %s: %s", image, exc)
        return False
    finally:
        try:
            client.close()
        except Exception:
            pass


def gc_orphan_containers(ttl_hours: int = 24) -> int:
    """Remove stopped sandbox containers left behind by crashed deletes.

    A container is only a candidate when it carries SANDBOX_LABEL, is not
    running, and finished longer than *ttl_hours* ago — a stopped container
    younger than that may still be re-adopted by its chat, because the backend
    deliberately keeps sandboxes on disk across a restart.
    """
    if ttl_hours <= 0:
        return 0
    try:
        import docker as _docker

        client = _docker.from_env(timeout=60)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sandbox GC skipped: %s", exc)
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    removed = 0
    try:
        for container in client.containers.list(
            all=True, filters={"label": SANDBOX_LABEL}
        ):
            try:
                if container.status == "running":
                    continue
                finished = (container.attrs.get("State") or {}).get("FinishedAt") or ""
                # A never-started container reports 0001-01-01; skip it rather
                # than treating it as ancient history.
                if not finished.startswith("2"):
                    continue
                if datetime.fromisoformat(finished.replace("Z", "+00:00")) > cutoff:
                    continue
                container.remove(force=True, v=True)
                removed += 1
            except Exception as exc:  # noqa: BLE001 — one bad container, not the sweep
                logger.debug("Sandbox GC could not remove %s: %s", container.name, exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sandbox GC failed: %s", exc)
    finally:
        try:
            client.close()
        except Exception:
            pass

    if removed:
        logger.info("Sandbox GC removed %d orphaned container(s)", removed)
    return removed


def _container_dir(path: str) -> str:
    """Return the parent directory of *path* using forward slashes.

    On Windows, ``Path(path).parent`` converts ``/workspace/uploads`` into
    ``\\workspace\\uploads`` which breaks Docker SDK calls.  Container
    paths are always Linux paths, so we operate on strings directly.
    """
    if "/" in path:
        return path.rsplit("/", 1)[0]
    return "/"


def _container_filename(path: str) -> str:
    """Return the filename component of *path* using forward slashes."""
    if "/" in path:
        return path.rsplit("/", 1)[1]
    return path


class DockerBackend(BaseSandbox):
    """Sandbox backend that executes commands inside a Docker container.

    Extends BaseSandbox so all file operations (ls, read, write, edit, grep, glob)
    are delegated to server-side Python scripts via execute().

    The Docker SDK connection is lazily established on first use so the class
    can be instantiated even when the Docker daemon is not running (e.g. in
    tests or before the user starts Docker Desktop).

    Parameters
    ----------
    image : str
        Docker image.  Defaults to ``"python:3.12-slim"``.
    container_id : str | None
        ID of an already-running container to attach to.
    container_name : str | None
        Custom container name.  Defaults to ``"deepagents-{uuid}"``.
    workdir : str
        Working directory inside the container.  Defaults to ``"/workspace"``.
    auto_create : bool
        If *True* (default), creates the container on first use.
    keep_alive : bool
        If *True*, the container is not removed on ``close()``.
    default_timeout : int
        Default timeout in seconds for ``execute()``.  Defaults to 120.
    max_output_bytes : int
        Maximum bytes from command output.  Defaults to 100 000.
    docker_cmd : str
        Path to the Docker CLI binary.
    env : dict[str, str] | None
        Environment variables inside the container.
    volumes : list[str] | None
        Bind-mount specs like ``"/host:/container:rw"``.
    network : str | None
        Docker network.  Pass ``"none"`` for no network (the default: the
        sandbox never needs egress).
    sandbox_user : str | None
        ``uid:gid`` every agent-facing exec runs as.  Defaults to
        ``DEFAULT_SANDBOX_USER`` (``"1000:1000"``); ``None``/``""`` keeps the
        image's default user, which for most images means root — set this
        only if you supply an image whose workdir that user can write.
    client_timeout : int
        Docker SDK read timeout in seconds (default 180). Must stay above the
        exec timeout: it also bounds ``containers.run``, which takes 5-15s on
        Docker Desktop for Windows — the old hardcoded 5s made a cold create
        fail with a bare ReadTimeoutError.
    mem_limit, nano_cpus, pids_limit :
        Hard ceilings for the container.  ``None`` leaves the daemon default,
        which is "unlimited" — always pass them from config.
    """

    def __init__(  # noqa: PLR0913
        self,
        image: str = "python:3.12-slim",
        container_id: str | None = None,
        container_name: str | None = None,
        workdir: str = "/workspace",
        auto_create: bool = True,
        keep_alive: bool = False,
        default_timeout: int = 120,
        max_output_bytes: int = 100_000,
        docker_cmd: str = "docker",
        env: dict[str, str] | None = None,
        volumes: list[str] | None = None,
        network: str | None = "none",
        max_pool_size: int = 25,
        executor_workers: int = 12,
        client_timeout: int = 180,
        sandbox_user: str | None = DEFAULT_SANDBOX_USER,
        mem_limit: str | None = None,
        nano_cpus: int | None = None,
        pids_limit: int | None = None,
    ) -> None:
        self._image = image
        self._container_id = container_id
        self._container_name = container_name or f"deepagents-{uuid.uuid4().hex[:12]}"
        self._workdir = workdir
        self._auto_create = auto_create
        self._keep_alive = keep_alive
        self._default_timeout = default_timeout
        self._max_output_bytes = max_output_bytes
        self._docker_cmd = docker_cmd
        self._env = env or {}
        self._volumes = volumes or []
        self._network = network
        self._max_pool_size = max_pool_size
        self._client_timeout = client_timeout
        # Isolation knobs. `sandbox_user` is the uid:gid every agent-facing
        # exec drops to; None means "run as the image default" (root), which
        # is only correct for an image whose workdir that user can write.
        self._sandbox_user = (sandbox_user or "").strip() or None
        self._mem_limit = mem_limit
        self._nano_cpus = nano_cpus
        self._pids_limit = pids_limit
        # Serialises find-or-create. Session creation is already locked per
        # thread in app.py, but _ensure_container is also reached directly
        # (workspace init, uploads), and two concurrent first calls would
        # otherwise race into two `docker run`s and one name conflict.
        self._create_lock = threading.Lock()

        # Dedicated thread pool for async exec calls. Separated from the
        # default anyio pool so agent tool execution (long, blocking) and
        # artifact reads (short, frequent) don't contend for threads.
        self._executor = ThreadPoolExecutor(
            max_workers=executor_workers,
            thread_name_prefix="docker-exec",
        )

        # State
        self._container: Any | None = None
        self._cid: str | None = container_id
        self._started = False
        self._closed = False
        # _stopped tracks "stop without remove" so _ensure_container can
        # restart the container later (e.g. after a server restart calls
        # close(remove=False) on shutdown).
        self._stopped = False

        # Lazy Docker SDK detection — only check that the package is importable.
        # The actual client connection is deferred to _get_client().
        self._use_sdk = False
        self._client: Any | None = None
        try:
            import docker as _docker  # noqa: F401

            _docker.APIClient  # verify the attribute exists
            self._use_sdk = True
            logger.info("Docker SDK package available (connection deferred)")
        except ImportError:
            logger.info("Docker SDK not available — using docker CLI")

    # ------------------------------------------------------------------
    # Lazy Docker client
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Return a connected Docker SDK client, establishing the connection on first call.

        Uses a tuned connection pool size to handle concurrent exec calls
        without queuing (default 10 is too low for agent + polling).
        """
        if self._client is not None:
            return self._client
        import docker as _docker

        # Use from_env() which handles protocol detection (unix socket,
        # named pipe on Windows, TCP, etc.) — then configure the pool size
        # via the underlying API client.
        #
        # The timeout is the read timeout of EVERY request on this client,
        # including ``containers.run`` — and creating + starting a container
        # on Docker Desktop for Windows routinely takes 5-15s. A 5s value
        # (what this used to be) makes a cold ``docker run`` fail with a bare
        # ReadTimeoutError. A daemon that is down is not slow, it is absent:
        # the named pipe / socket refuses immediately, so fail-fast does not
        # depend on this number.
        try:
            self._client = _docker.from_env(
                max_pool_size=self._max_pool_size,
                timeout=self._client_timeout,
            )
        except Exception as exc:
            msg = (
                "Cannot connect to Docker. Make sure Docker Desktop "
                "is running, then restart the backend."
            )
            logger.error("%s (%s)", msg, exc)
            raise RuntimeError(msg) from exc
        logger.info(
            "Docker SDK client connected (max_pool_size=%d)",
            self._max_pool_size,
        )
        return self._client

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:  # noqa: A003
        """Unique identifier for this sandbox backend."""
        return self._container_name

    # ------------------------------------------------------------------
    # Container lifecycle
    # ------------------------------------------------------------------

    def _ensure_container(self) -> str:
        """Return the container ID, creating/starting the container if needed.

        Order of operations:
          1. If we already have a CID we believe is live, return it — with NO
             daemon round trip. ``_started`` is the fast-path flag; it is
             cleared on ``close()``, on a failed exec and on any state change,
             so a dead container costs one failed call, not one inspect per
             tool call (this was the single largest per-command latency cost:
             every agent tool call paid an extra ``containers.get``).
          2. Look up an existing container by deterministic name. If found
             and running, adopt it. If found and stopped, ``docker start``
             it and adopt. This is how the backend reattaches to a chat's
             container after a server restart.
          3. Otherwise create a fresh container.

        Serialised: two concurrent first calls would otherwise race into two
        ``docker run``s and one name conflict.
        """
        if self._cid is not None and self._started and not self._stopped:
            return self._cid

        with self._create_lock:
            # Double-check: another thread may have finished the work while
            # this one waited on the lock.
            if self._cid is not None and self._started and not self._stopped:
                return self._cid

            # Try to reattach to an existing container with the deterministic
            # name.
            cid, running = self._find_by_name(self._container_name)
            if cid is not None:
                if not running:
                    self._start_existing(cid)
                self._cid = cid
                self._started = True
                self._stopped = False
                logger.info(
                    "Reattached to existing container %s (%s)",
                    self._container_name,
                    cid[:12],
                )
                # A container created before the sandbox dropped to a
                # non-root user owns a root-owned workdir; without this the
                # agent's first write fails with EACCES. No-op when the
                # workdir is already accessible.
                self._grant_workdir_access()
                return cid

            if self._auto_create:
                return self._create_container()
        msg = (
            "No running Docker container available and auto_create=False. "
            "Provide a container_id or set auto_create=True."
        )
        raise RuntimeError(msg)

    def _grant_workdir_access(self) -> None:
        """Make the workdir writable for the sandbox user (root exec, best effort).

        chmod rather than chown because ``cap_drop=["ALL"]`` removes CAP_CHOWN
        (see ``_startup_command``). Recursive AND best-effort: root without
        CAP_FOWNER cannot chmod the agent's own files, so most of the tree
        reports "Operation not permitted" — that is expected, and the ``|| true`
        keeps it from looking like a failure. It exists to rescue root-owned
        files left by a pre-hardening container.
        """
        if not self._sandbox_user:
            return
        try:
            self._exec_as_root(
                f"chmod -R a+rwX {shlex.quote(self._workdir)} 2>/dev/null || true"
            )
        except Exception as exc:  # noqa: BLE001 — never block the container
            logger.debug("Could not open up workdir %s: %s", self._workdir, exc)

    def _find_by_name(self, name: str) -> tuple[str | None, bool]:
        """Look up a container by name. Returns (cid, is_running) or (None, False)."""
        if self._use_sdk:
            try:
                c = self._get_client().containers.get(name)
                return c.id, c.status == "running"
            except Exception:
                return None, False
        result = subprocess.run(
            [
                self._docker_cmd,
                "inspect",
                "--format",
                "{{.Id}} {{.State.Running}}",
                name,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None, False
        parts = result.stdout.strip().split()
        if len(parts) != 2:
            return None, False
        cid, running_flag = parts
        return cid, running_flag.lower() == "true"

    def _start_existing(self, cid: str) -> None:
        """Start a stopped container by ID or name."""
        if self._use_sdk:
            try:
                self._get_client().containers.get(cid).start()
                return
            except Exception as exc:
                logger.warning("SDK start failed for %s, falling back to CLI: %s", cid[:12], exc)
        subprocess.run(
            [self._docker_cmd, "start", cid],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _create_container(self) -> str:
        """Create and start a new Docker container."""
        if self._use_sdk:
            return self._create_via_sdk()
        return self._create_via_cli()

    def _hardening_kwargs(self) -> dict[str, Any]:
        """Daemon-side isolation settings shared by both creation paths.

        Kept in one place so the CLI fallback cannot drift from the SDK path:
        a container created by the fallback must be exactly as confined as one
        created by the SDK, or the fallback silently becomes the weak path.
        """
        kwargs: dict[str, Any] = {
            "init": True,  # tini as PID 1: reaps zombies, forwards signals
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
        }
        if self._pids_limit:
            kwargs["pids_limit"] = self._pids_limit
        if self._mem_limit:
            kwargs["mem_limit"] = self._mem_limit
        if self._nano_cpus:
            kwargs["nano_cpus"] = self._nano_cpus
        return kwargs

    def _startup_command(self) -> list[str]:
        """The container's PID-1 command: open the workdir, then idle.

        Folding this into the command instead of a follow-up ``docker exec``
        removes one daemon round trip from every container creation.

        It grants access with ``chmod``, not ``chown``: the container runs with
        ``cap_drop=["ALL"]``, which removes CAP_CHOWN, so a root chown fails
        with "Operation not permitted" — and a failing ``&&` chain here takes
        PID 1 down with it, i.e. the container exits during creation.

        Non-recursive on purpose: root without CAP_FOWNER may only chmod what
        it owns, so a recursive pass over agent-created files (uid 1000) fails
        on every one of them. The workdir itself is root-owned at this point;
        everything the agent creates inside it is already its own.
        """
        if not self._sandbox_user:
            return ["tail", "-f", "/dev/null"]
        workdir = shlex.quote(self._workdir)
        return [
            "/bin/sh",
            "-c",
            f"mkdir -p {workdir} && chmod a+rwX {workdir} && "
            "exec tail -f /dev/null",
        ]

    def _create_via_sdk(self) -> str:
        """Create container using the Docker Python SDK."""
        client = self._get_client()
        volumes_dict: dict[str, dict[str, str]] = {}
        for vol in self._volumes:
            parts = vol.split(":")
            host_path = parts[0]
            container_path = parts[1] if len(parts) > 1 else parts[0]
            mode = parts[2] if len(parts) > 2 else "rw"
            volumes_dict[host_path] = {"bind": container_path, "mode": mode}

        self._container = client.containers.run(
            self._image,
            command=self._startup_command(),
            name=self._container_name,
            working_dir=self._workdir,
            detach=True,
            auto_remove=False,
            volumes=volumes_dict or None,
            network=self._network,
            environment=self._env_with_home(),
            labels={SANDBOX_LABEL: "1", THREAD_LABEL: self._container_name},
            **self._hardening_kwargs(),
        )
        self._cid = self._container.id
        self._started = True
        self._stopped = False
        logger.info(
            "Created Docker container %s (%s) user=%s net=%s mem=%s pids=%s",
            self._container_name,
            self._cid[:12],
            self._sandbox_user or "image-default",
            self._network,
            self._mem_limit or "unlimited",
            self._pids_limit or "unlimited",
        )
        return self._cid

    def _env_with_home(self) -> dict[str, str] | None:
        """Container env, with a writable HOME for the non-root sandbox user.

        Without this the image's ``HOME=/root`` is inherited, and a non-root
        ``pip install --user`` / ``git config`` fails on an unwritable home.
        ``/tmp`` is world-writable in every slim base image.
        """
        env = dict(self._env)
        if self._sandbox_user:
            env.setdefault("HOME", "/tmp")
        return env or None

    def _create_via_cli(self) -> str:
        """Create container using the Docker CLI."""
        cmd = [
            self._docker_cmd,
            "run",
            "-d",
            "--name",
            self._container_name,
            "-w",
            self._workdir,
            "--init",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--label",
            f"{SANDBOX_LABEL}=1",
            "--label",
            f"{THREAD_LABEL}={self._container_name}",
        ]
        if self._pids_limit:
            cmd.extend(["--pids-limit", str(self._pids_limit)])
        if self._mem_limit:
            cmd.extend(["--memory", str(self._mem_limit)])
        if self._nano_cpus:
            cmd.extend(["--cpus", str(self._nano_cpus / 1_000_000_000)])
        for k, v in (self._env_with_home() or {}).items():
            cmd.extend(["-e", f"{k}={v}"])
        for vol in self._volumes:
            cmd.extend(["-v", vol])
        if self._network:
            cmd.extend(["--network", self._network])
        cmd.extend([self._image, *self._startup_command()])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            msg = f"Failed to create Docker container: {result.stderr}"
            raise RuntimeError(msg)

        self._cid = result.stdout.strip()
        self._started = True
        self._stopped = False
        logger.info(
            "Created Docker container %s (%s) via CLI", self._container_name, self._cid[:12]
        )
        return self._cid

    # ------------------------------------------------------------------
    # Close / cleanup
    # ------------------------------------------------------------------

    def close(self, *, remove: bool = True) -> None:
        """Stop the Docker container and optionally remove it.

        Parameters
        ----------
        remove:
            If True (default) the container is stopped and removed — used
            when a chat is deleted. If False the container is stopped but
            left on disk so it can be ``docker start``ed again by
            ``_ensure_container`` — used when the server shuts down while
            chats are still active.
        """
        if self._closed:
            return
        if remove:
            self._closed = True

        # Shut down the dedicated exec thread pool WITHOUT waiting: an exec
        # still blocked inside the daemon (a command the ``timeout` wrapper
        # could not reap) would otherwise hang the DELETE request or the
        # shutdown handler for as long as it runs. Running tasks keep their
        # reference to the pool; queued ones are dropped.
        if hasattr(self, '_executor') and self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

        if self._cid is None or not self._started:
            return

        # `keep_alive` is the shutdown-survival flag — it tells the lifespan
        # handler to leave the container on disk so workspace state survives
        # a backend restart. It must NOT block an explicit user-initiated
        # delete (remove=True from DELETE /session/{id}); otherwise deleting
        # a chat leaves its sandbox orphaned forever.
        if self._keep_alive and not remove:
            logger.info("Keeping container %s alive (keep_alive=True)", self._cid[:12])
            return

        # PID 1 is ``tail -f /dev/null`` behind tini: nothing to drain, so a
        # 1s grace period is plenty. The default 10s made every chat delete
        # and every shutdown feel hung.
        if self._use_sdk:
            try:
                c = self._get_client().containers.get(self._cid)
                c.stop(timeout=1)
                if remove:
                    # v=True drops anonymous volumes with the container; the
                    # labelled sandbox is single-use, so nothing should leak.
                    c.remove(v=True)
                    self._started = False
                    logger.info("Stopped and removed container %s", self._cid[:12])
                else:
                    self._stopped = True
                    self._started = False
                    logger.info("Stopped container %s (kept on disk)", self._cid[:12])
            except Exception as exc:
                logger.warning("Failed to stop/remove container via SDK: %s", exc)
        else:
            try:
                subprocess.run(
                    [self._docker_cmd, "stop", "-t", "1", self._cid],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if remove:
                    subprocess.run(
                        [self._docker_cmd, "rm", "-v", self._cid],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self._started = False
                    logger.info("Stopped and removed container %s", self._cid[:12])
                else:
                    self._stopped = True
                    self._started = False
                    logger.info("Stopped container %s (kept on disk)", self._cid[:12])
            except Exception as exc:
                logger.warning("Failed to stop/remove container via CLI: %s", exc)

    # ------------------------------------------------------------------
    # Core abstract methods (BaseSandbox)
    # ------------------------------------------------------------------

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Execute a shell command inside the Docker container."""
        cid = self._ensure_container()
        effective_timeout = timeout or self._default_timeout

        if self._use_sdk:
            return self._exec_via_sdk(command, effective_timeout)
        return self._exec_via_cli(cid, command, effective_timeout)

    async def execute_async(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Async wrapper around execute().

        Runs the synchronous execute() in a dedicated thread pool so the
        event loop stays free for other requests.  Uses a separate pool
        (not the default anyio one) so artifact reads don't contend with
        agent tool calls for thread slots.
        """
        effective_timeout = timeout or self._default_timeout
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.execute(command, timeout=effective_timeout),
        )

    async def download_file_async(self, path: str) -> bytes | None:
        """Async wrapper around download_files() for a single file.

        Runs the synchronous Docker file download (docker cp / get_archive)
        in the dedicated exec thread pool so the event loop stays free.
        Returns the raw bytes, or None if the file wasn't found.
        """
        loop = asyncio.get_running_loop()
        results: list[FileDownloadResponse] = await loop.run_in_executor(
            self._executor,
            self.download_files,
            [path],
        )
        if not results:
            return None
        resp = results[0]
        if resp.error:
            logger.warning("download_file_async error for %s: %s", path, resp.error)
            return None
        return resp.content

    def _cap_output(self, output: str) -> tuple[str, bool]:
        """Cap oversized command output and TELL the model it was cut.

        Two bugs this replaces:

        1. The notice was missing entirely. `truncated=True` was set on the
           response but no caller anywhere reads that flag, so the agent
           received a silently shortened file and had no way to know the
           tail existed — it would answer from, and extrapolate beyond, a
           partial read. deepagents' own `local_shell` backend appends an
           in-band marker for exactly this reason; this matches it.
        2. The cap mixed units: the check measured UTF-8 *bytes* while the
           slice counted *characters*, so non-ASCII output (the German
           source documents in this project) could keep up to ~4x the
           intended byte budget. Slice the encoded bytes instead, and drop
           any partial character left at the boundary.
        """
        raw = output.encode("utf-8")
        if len(raw) <= self._max_output_bytes:
            return output, False
        clipped = raw[: self._max_output_bytes].decode("utf-8", errors="ignore")
        return (
            clipped
            + f"\n\n... Output truncated at {self._max_output_bytes} bytes. "
            "Re-run scoped to the part you need (head/tail/sed -n/grep) — "
            "do NOT infer the omitted content.",
            True,
        )

    def _exec_cmd(self, command: str, timeout: int) -> list[str]:
        """Wrap *command* in coreutils ``timeout``.

        ``docker exec`` has no timeout of its own: without this wrapper a hung
        command holds its executor thread — and the container — until the
        process dies, so twelve of them wedge the chat's sandbox for the life
        of the backend. ``timeout`` signals the whole process group, so
        grandchildren die too, and exits 124, which callers report as a
        timeout rather than as a generic failure.
        """
        return [
            "timeout",
            "-k",
            str(_TIMEOUT_KILL_GRACE_S),
            f"{int(timeout)}s",
            "/bin/sh",
            "-c",
            command,
        ]

    def _container_handle(self) -> Any:
        """Cached SDK container handle.

        Every ``containers.get`` is a daemon round trip, and the agent issues
        one command per tool call plus an artifact poll every 2s — reusing the
        handle removes that from the hot path. The handle stays valid because
        it only carries the container id; if the container is gone the next
        ``exec_run` raises, which clears both ``_started`` and the handle.
        """
        if self._container is not None and self._started:
            return self._container
        self._container = self._get_client().containers.get(self._ensure_container())
        return self._container

    def _exec_as_root(self, command: str, timeout: int = 30) -> None:
        """Run a command as the container's own user (root), not the sandbox user.

        Only for ownership fixes — the agent never routes through here.
        """
        if self._use_sdk:
            self._container_handle().exec_run(
                cmd=["/bin/sh", "-c", command], user="0:0", demux=True
            )
            return
        subprocess.run(
            [
                self._docker_cmd,
                "exec",
                "-u",
                "0:0",
                self._ensure_container(),
                "/bin/sh",
                "-c",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _exec_via_sdk(self, command: str, timeout: int) -> ExecuteResponse:
        """Execute command using the Docker Python SDK."""
        try:
            exec_result = self._container_handle().exec_run(
                cmd=self._exec_cmd(command, timeout),
                workdir=self._workdir,
                user=self._sandbox_user,
                demux=True,
            )
            exit_code = exec_result.exit_code
            stdout, stderr = exec_result.output
            output = ""
            if stdout:
                output += stdout.decode("utf-8", errors="replace")
            if stderr:
                output += stderr.decode("utf-8", errors="replace")

            if exit_code == 124:
                output += (
                    f"\n\nCommand timed out after {timeout}s and was killed. "
                    "Narrow the command (head/tail/sed -n, a tighter glob) or "
                    "split it into smaller steps."
                )

            output, truncated = self._cap_output(output)

            return ExecuteResponse(
                output=output,
                exit_code=exit_code,
                truncated=truncated,
            )
        except Exception as exc:
            # A transport-level failure (container gone, daemon restarted)
            # means the cached "running" belief is stale: drop it so the next
            # call re-probes instead of failing the same way forever.
            self._started = False
            self._container = None
            logger.error("SDK exec failed: %s", exc)
            return ExecuteResponse(
                output=f"Error executing command: {exc}",
                exit_code=1,
                truncated=False,
            )

    def _exec_via_cli(self, cid: str, command: str, timeout: int) -> ExecuteResponse:
        """Execute command using the Docker CLI."""
        cmd = [
            self._docker_cmd,
            "exec",
            "-w",
            self._workdir,
        ]
        if self._sandbox_user:
            cmd.extend(["-u", self._sandbox_user])
        cmd.extend([cid, *self._exec_cmd(command, timeout)])
        try:
            # Client-side timeout stays as a backstop (a wedged daemon
            # connection), but the in-container ``timeout`` above is what
            # actually kills the command.
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + _TIMEOUT_KILL_GRACE_S + 5,
            )

            output, truncated = self._cap_output(result.stdout + result.stderr)

            return ExecuteResponse(
                output=output,
                exit_code=result.returncode,
                truncated=truncated,
            )
        except subprocess.TimeoutExpired:
            return ExecuteResponse(
                output=f"Command timed out after {timeout} seconds",
                exit_code=124,
                truncated=False,
            )
        except Exception as exc:
            logger.error("CLI exec failed: %s", exc)
            return ExecuteResponse(
                output=f"Error executing command: {exc}",
                exit_code=1,
                truncated=False,
            )

    # ------------------------------------------------------------------
    # File transfer
    # ------------------------------------------------------------------

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        """Upload files into the Docker container.

        Creates parent directories as needed. Uses ``put_archive`` for SDK
        mode and ``docker cp`` for CLI mode.

        Container paths always use forward slashes — on Windows, ``Path()``
        converts ``/`` to ``\\`` which breaks Docker SDK calls, so we use
        string-based path splitting instead.
        """
        cid = self._ensure_container()
        responses: list[FileUploadResponse] = []
        uploaded: set[str] = set()

        for container_path, content in files:
            try:
                parent = _container_dir(container_path)
                self.execute(f"mkdir -p {shlex.quote(parent)}")

                if self._use_sdk:
                    self._upload_via_sdk(container_path, content)
                else:
                    self._upload_via_cli(cid, container_path, content)

                responses.append(FileUploadResponse(path=container_path))
                uploaded.add(container_path)
            except Exception as exc:
                logger.error("Failed to upload %s: %s", container_path, exc)
                responses.append(FileUploadResponse(path=container_path, error=str(exc)))

        # put_archive writes as the daemon (root) regardless of the exec user,
        # so a freshly uploaded file would be read-only for the agent — and
        # edit_file on an uploaded source document is a normal thing to do.
        # Per-file, not recursive: the daemon creates the file root-owned, but
        # the parent directory usually already belongs to the sandbox user,
        # and root without CAP_FOWNER cannot chmod that. Best-effort, because
        # the upload itself already succeeded.
        if uploaded and self._sandbox_user:
            quoted = " ".join(shlex.quote(p) for p in sorted(uploaded))
            try:
                self._exec_as_root(f"chmod a+rwX {quoted} 2>/dev/null || true")
            except Exception as exc:  # noqa: BLE001 — upload already succeeded
                logger.warning("Could not open up uploaded files: %s", exc)

        return responses

    def _upload_via_sdk(self, container_path: str, content: bytes) -> None:
        """Upload a file using the Docker SDK (put_archive).

        Uses ``_container_dir`` / ``_container_filename`` instead of
        ``Path()`` to keep forward slashes on Windows.
        """
        container = self._container_handle()

        parent = _container_dir(container_path)
        filename = _container_filename(container_path)

        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            info = tarfile.TarInfo(name=filename)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        tar_stream.seek(0)

        container.put_archive(parent, tar_stream)

    def _upload_via_cli(self, cid: str, container_path: str, content: bytes) -> None:
        """Upload a file using docker cp via a temp file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [self._docker_cmd, "cp", tmp_path, f"{cid}:{container_path}"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                msg = f"docker cp failed: {result.stderr}"
                raise RuntimeError(msg)
        finally:
            os.unlink(tmp_path)

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Download files from the Docker container.

        Container paths always use forward slashes — same Windows fix as
        ``upload_files``.
        """
        cid = self._ensure_container()
        responses: list[FileDownloadResponse] = []

        for path in paths:
            try:
                if self._use_sdk:
                    content = self._download_via_sdk(path)
                else:
                    content = self._download_via_cli(cid, path)
                responses.append(FileDownloadResponse(path=path, content=content))
            except Exception as exc:
                logger.error("Failed to download %s: %s", path, exc)
                responses.append(FileDownloadResponse(path=path, error=str(exc)))

        return responses

    def _download_via_sdk(self, container_path: str) -> bytes:
        """Download a file using the Docker SDK (get_archive)."""
        container = self._container_handle()

        parent = _container_dir(container_path)
        filename = _container_filename(container_path)

        # Fetch the file itself, not its parent directory: get_archive(parent)
        # buffers a tar of every sibling into memory to read one member.
        stream, _ = container.get_archive(container_path)
        tar_data = b"".join(chunk for chunk in stream)

        tar_stream = io.BytesIO(tar_data)
        with tarfile.open(fileobj=tar_stream, mode="r") as tar:
            # Single pass: match by exact name, then by basename fallback.
            for member in tar.getmembers():
                match = member.name == filename or member.name.endswith("/" + filename)
                if not match:
                    member_filename = member.name.rsplit("/", 1)[-1] if "/" in member.name else member.name
                    match = member_filename == filename
                if match:
                    f = tar.extractfile(member)
                    if f is not None:
                        return f.read()

        msg = f"File {filename} not found in archive"
        raise FileNotFoundError(msg)

    def _download_via_cli(self, cid: str, container_path: str) -> bytes:
        """Download a file using docker cp via a temp file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [self._docker_cmd, "cp", f"{cid}:{container_path}", tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                msg = f"docker cp failed: {result.stderr}"
                raise RuntimeError(msg)

            return Path(tmp_path).read_bytes()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def glob(self, pattern: str, path: str = "/workspace") -> Any:
        """Structured glob matching, restricted to workspace to prevent hangs."""
        if path == "/":
            path = self._workdir
        return super().glob(pattern, path)

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> Any:
        """Search file contents, restricted to workspace to prevent hangs."""
        if path == "/":
            path = self._workdir
        return super().grep(pattern, path, glob)

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------

    def __del__(self) -> None:  # type: ignore[misc]
        """Release local resources on garbage collection.

        Deliberately does NOT stop or remove the Docker container. Container
        lifecycle is explicit:
          * removed only by an explicit ``close(remove=True)`` (chat deletion,
            via ``_destroy_session``),
          * stopped-but-kept by ``close(remove=False)`` on server shutdown,
          * otherwise left running so the next message re-adopts it by name.

        The previous implementation called ``self.close()`` here, which
        defaults to ``remove=True`` and bypasses the ``keep_alive`` guard
        (that guard only protects the ``remove=False`` path). That meant
        garbage-collecting a backend — which happens every time
        ``_invalidate_all_orchestrators`` clears the session cache (e.g. on
        any custom-agent create/update/delete) — destroyed the chat's
        container and its entire workspace. Releasing only the thread pool
        here keeps the container alive for re-adoption.
        """
        executor = getattr(self, "_executor", None)
        if executor is not None:
            try:
                executor.shutdown(wait=False)
            except Exception:
                pass

    def __enter__(self) -> DockerBackend:
        self._ensure_container()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()