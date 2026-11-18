"""Storage for runtime-tunable model settings (base URL, API key, models).

Lets the user point the harness at a different OpenAI-compatible endpoint
or swap the agent / vision model from the Settings panel without editing
``.env`` and restarting. One base URL + one API key are shared by both the
text agent model and the multimodal vision-review model; only the model
*names* differ.

Resolution order, highest priority first:
  1. Values stored in ``backend/data/model_settings.json`` (set via the
     Settings panel in the frontend).
  2. The corresponding ``config`` constant — which already folds in the
     environment variable (``OPENAI_BASE_URL``, ``OPENAI_API_KEY``,
     ``AGENT_MODEL``, ``VISION_MODEL``) and the built-in default.

So a deployment configured via env vars and a developer configuring from
the UI coexist without clobbering each other.

Note: model changes take effect for NEW chat sessions (each builds its
model via ``agent._build_model`` at creation time). Existing in-memory
sessions keep the model they were created with.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from sdlc.core import config

logger = logging.getLogger(__name__)

_SETTINGS_PATH = Path(config.CHECKPOINT_DB_PATH).parent / "model_settings.json"
_write_lock = threading.Lock()

# Keys this store manages. Defaults are read live from ``config`` (which is
# env-or-builtin), so the JSON store only needs to hold explicit overrides.
_DEFAULT_SOURCES: dict[str, str] = {
    "model_provider": "MODEL_PROVIDER",
    "reasoning_effort": "REASONING_EFFORT",
    "base_url": "OPENAI_BASE_URL",
    "api_key": "OPENAI_API_KEY",
    "agent_model": "MODEL_NAME",
    "vision_model": "VISION_MODEL",
    "retry_model": "RETRY_MODEL",
}

_VALID_KEYS = set(_DEFAULT_SOURCES.keys())
# Keys whose values must never be returned to the client in clear text.
SECRET_KEYS = {"api_key"}


def _config_default(key: str) -> str:
    """Return the config-level default for *key* (env var or built-in)."""
    return str(getattr(config, _DEFAULT_SOURCES[key], "") or "")


def _load_raw() -> dict[str, str]:
    """Return the stored overrides dict (or {} if absent / malformed)."""
    if not _SETTINGS_PATH.exists():
        return {}
    try:
        with _SETTINGS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("model_settings.json is not a dict — treating as empty")
            return {}
        return {k: str(v) for k, v in data.items() if k in _VALID_KEYS}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read model_settings.json: %s — treating as empty", exc)
        return {}


def _save_raw(settings: dict[str, str]) -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _SETTINGS_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    tmp.replace(_SETTINGS_PATH)


# ── Public API ──────────────────────────────────────────────────────────


def get_effective_settings() -> dict[str, str]:
    """Resolve all model settings via the stored-override > config cascade.

    Returns a dict with all keys populated, INCLUDING the raw ``api_key`` —
    for internal use by model construction only. Never return this verbatim
    to the client; mask ``api_key`` at the API boundary.
    """
    stored = _load_raw()
    out: dict[str, str] = {}
    for key in _VALID_KEYS:
        out[key] = stored[key] if stored.get(key) else _config_default(key)
    return out


def get_stored_settings() -> dict[str, str]:
    """Return only the JSON-stored overrides (no config fallback).

    Used by the Settings UI to show which fields are explicitly overridden
    vs. inheriting from env/default.
    """
    return _load_raw()


def update_settings(updates: dict[str, Any]) -> dict[str, str]:
    """Merge *updates* into the stored overrides. Returns the new effective view.

    Empty-string values clear an override (the field falls back to config).
    Unknown keys are rejected.
    """
    for key in updates:
        if key not in _VALID_KEYS:
            msg = f"Unknown model setting key: {key!r}"
            raise ValueError(msg)

    with _write_lock:
        stored = _load_raw()
        for key, value in updates.items():
            value_str = "" if value is None else str(value).strip()
            if value_str:
                stored[key] = value_str
            else:
                stored.pop(key, None)
        _save_raw(stored)
        # Log key names only — never the values (one is a secret).
        logger.info("Model settings updated: %s", list(updates.keys()))
    return get_effective_settings()
