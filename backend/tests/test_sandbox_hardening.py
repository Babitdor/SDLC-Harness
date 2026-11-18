"""Isolation and lifecycle invariants of the Docker sandbox backend.

These tests never talk to a Docker daemon — a fake client records what the
backend asks for. They exist because the sandbox is the boundary between
untrusted uploaded documents and the host: a regression here (a dropped
cap_drop, a lost ``timeout`` wrapper, a container reattached as root) is
silent in production and expensive in the incident review.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import docker
import pytest

from sdlc.sandbox import docker_backend as mod
from sdlc.sandbox.docker_backend import DockerBackend


class FakeExecResult:
    def __init__(self, exit_code: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> None:
        self.exit_code = exit_code
        self.output = (stdout, stderr)


class FakeContainer:
    def __init__(self, name: str = "harness-t", status: str = "running") -> None:
        self.id = "c" * 64
        self.name = name
        self.status = status
        self.attrs = {"State": {"FinishedAt": "2020-01-01T00:00:00Z"}}
        self.execs: list[dict] = []
        self.removed: dict | None = None
        self.stopped: float | None = None

    def exec_run(self, cmd, **kwargs):  # noqa: ANN001, ANN003
        self.execs.append({"cmd": list(cmd), **kwargs})
        return FakeExecResult()

    def stop(self, timeout: float | None = None) -> None:
        self.stopped = timeout
        self.status = "exited"

    def remove(self, **kwargs) -> None:  # noqa: ANN003
        self.removed = kwargs


class FakeContainers:
    def __init__(self, container: FakeContainer | None = None, listed=None) -> None:
        self._container = container
        self._listed = listed or []
        self.run_calls: list[dict] = []
        self.get_calls = 0

    def get(self, ident):  # noqa: ANN001
        self.get_calls += 1
        if self._container is None:
            raise RuntimeError("not found")
        return self._container

    def run(self, image, **kwargs):  # noqa: ANN001, ANN003
        self.run_calls.append({"image": image, **kwargs})
        self._container = FakeContainer(name=kwargs.get("name", "harness-t"))
        return self._container

    def list(self, all=True, filters=None):  # noqa: ANN001, ANN201
        return self._listed


class FakeClient:
    def __init__(self, container: FakeContainer | None = None, listed=None) -> None:
        self.containers = FakeContainers(container, listed)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def make_backend(container: FakeContainer | None = None) -> tuple[DockerBackend, FakeClient]:
    backend = DockerBackend(
        container_name="harness-t",
        mem_limit="2g",
        nano_cpus=1_000_000_000,
        pids_limit=256,
    )
    client = FakeClient(container)
    backend._client = client
    backend._use_sdk = True
    return backend, client


def test_creation_applies_isolation_floor() -> None:
    backend, client = make_backend()

    backend._ensure_container()

    call = client.containers.run_calls[0]
    assert call["cap_drop"] == ["ALL"]
    assert call["security_opt"] == ["no-new-privileges:true"]
    assert call["init"] is True
    assert call["pids_limit"] == 256
    assert call["mem_limit"] == "2g"
    assert call["nano_cpus"] == 1_000_000_000
    assert call["network"] == "none"
    assert call["labels"] == {mod.SANDBOX_LABEL: "1", mod.THREAD_LABEL: "harness-t"}
    # The workdir is opened by the container's own PID 1, not by a second
    # exec: that saves a daemon round trip on every creation. chmod, not
    # chown — CAP_CHOWN is dropped, and a failing chown kills PID 1.
    assert "chmod a+rwX /workspace" in " ".join(call["command"])
    assert call["environment"] == {"HOME": "/tmp"}


def test_exec_drops_to_sandbox_user_with_timeout_wrapper() -> None:
    container = FakeContainer()
    backend, _client = make_backend(container)

    backend.execute("echo hi", timeout=30)

    # First exec is the reattach chown (root); the command itself runs as the
    # sandbox user, wrapped in coreutils timeout.
    assert container.execs[0]["user"] == "0:0"
    cmd_exec = container.execs[-1]
    assert cmd_exec["user"] == "1000:1000"
    assert cmd_exec["cmd"][:4] == ["timeout", "-k", "5", "30s"]
    assert cmd_exec["cmd"][-1] == "echo hi"


def test_timeout_exit_code_is_explained() -> None:
    container = FakeContainer()
    backend, _client = make_backend(container)
    container.exec_run = lambda cmd, **kwargs: FakeExecResult(124)  # type: ignore[method-assign]

    resp = backend.execute("sleep 999")

    assert resp.exit_code == 124
    assert "timed out after 120s" in resp.output


def test_warm_container_skips_liveness_probe() -> None:
    container = FakeContainer()
    backend, client = make_backend(container)

    backend.execute("true")
    probes_after_first = client.containers.get_calls
    backend.execute("true")

    # The second command must not pay a containers.get round trip.
    assert client.containers.get_calls == probes_after_first


def test_upload_reclaims_ownership_for_the_agent() -> None:
    container = FakeContainer()
    backend, _client = make_backend(container)
    backend._upload_via_sdk = lambda path, content: None  # type: ignore[method-assign]

    responses = backend.upload_files([("/workspace/uploads/a.md", b"x")])

    assert responses[0].error is None
    opens = [
        e
        for e in container.execs
        if e["user"] == "0:0" and "chmod a+rwX /workspace/uploads/a.md" in " ".join(e["cmd"])
    ]
    assert opens, "uploaded files must be writable for the sandbox user"


def test_close_stops_fast_and_drops_volumes() -> None:
    container = FakeContainer()
    backend, _client = make_backend(container)
    backend.execute("true")

    backend.close(remove=True)

    assert container.stopped == 1  # 1s grace, not the daemon default 10s
    assert container.removed == {"v": True}


def test_gc_removes_only_old_stopped_sandboxes(monkeypatch: pytest.MonkeyPatch) -> None:
    old = FakeContainer(name="harness-old", status="exited")
    old.attrs = {"State": {"FinishedAt": "2020-01-01T00:00:00Z"}}
    fresh = FakeContainer(name="harness-fresh", status="exited")
    fresh.attrs = {
        "State": {
            "FinishedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
    }
    running = FakeContainer(name="harness-live", status="running")
    client = FakeClient(listed=[old, fresh, running])
    monkeypatch.setattr(docker, "from_env", lambda **kwargs: client)

    removed = mod.gc_orphan_containers(ttl_hours=24)

    assert removed == 1
    assert old.removed == {"force": True, "v": True}
    assert fresh.removed is None
    assert running.removed is None


def test_ensure_image_pulls_only_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeImages:
        def __init__(self, present: bool) -> None:
            self.present = present
            self.pulled: list[str] = []

        def get(self, image: str):
            if not self.present:
                raise RuntimeError("No such image")
            return SimpleNamespace(id="sha256:x")

        def pull(self, image: str):
            self.pulled.append(image)
            return SimpleNamespace(id="sha256:y")

    client = FakeClient()
    client.images = FakeImages(present=True)  # type: ignore[attr-defined]
    monkeypatch.setattr(docker, "from_env", lambda **kwargs: client)
    assert mod.ensure_image("python:3.12-slim") is True
    assert client.images.pulled == []  # type: ignore[attr-defined]

    client.images = FakeImages(present=False)  # type: ignore[attr-defined]
    assert mod.ensure_image("python:3.12-slim") is True
    assert client.images.pulled == ["python:3.12-slim"]  # type: ignore[attr-defined]


def test_ensure_image_never_raises_without_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**kwargs):  # noqa: ANN003, ANN202
        raise RuntimeError("daemon down")

    monkeypatch.setattr(docker, "from_env", boom)
    assert mod.ensure_image("python:3.12-slim") is False
    assert mod.gc_orphan_containers(ttl_hours=24) == 0
