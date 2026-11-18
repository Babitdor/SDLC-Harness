"""File upload handling — copies uploaded files into the Docker container."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from sdlc.sandbox.docker_backend import DockerBackend

from sdlc.core.config import UPLOAD_DIR_HOST

logger = logging.getLogger(__name__)


async def upload_file_to_container(
    backend: DockerBackend,
    thread_id: str,
    filename: str,
    content: bytes,
    target_dir: str | None = None,
) -> str:
    """Upload a file into the Docker container.

    Args:
        backend: The DockerBackend instance.
        thread_id: Conversation thread ID (used to namespace uploads).
        filename: Original filename (safe-stripped).
        content: Raw file bytes.
        target_dir: Container-absolute directory to upload into.
            Defaults to ``/workspace/uploads/{thread_id}``.

    Returns:
        The container-absolute path where the file was stored.
    """
    # Sanitise filename
    safe_name = Path(filename).name.replace(" ", "_")

    if target_dir:
        container_dir = target_dir
    else:
        container_dir = f"/workspace/uploads/{thread_id}"

    container_path = f"{container_dir}/{safe_name}"

    # Ensure the directory exists inside the container
    result = backend.execute(f"mkdir -p {container_dir}")
    if result.exit_code != 0:
        logger.error("mkdir failed in container: %s", result.output)
        msg = f"Failed to create directory {container_dir} in container"
        raise RuntimeError(msg)

    # Upload the file
    responses = backend.upload_files([(container_path, content)])
    if responses and responses[0].error:
        msg = f"Upload failed: {responses[0].error}"
        raise RuntimeError(msg)

    logger.info("Uploaded %s (%d bytes) → %s", safe_name, len(content), container_path)
    return container_path


def ensure_host_upload_dir() -> None:
    """Create the host-side upload staging directory if it doesn't exist."""
    upload_dir = Path(UPLOAD_DIR_HOST).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Host upload directory: %s", upload_dir)