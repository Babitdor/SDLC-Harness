"""Human-in-the-loop (HITL) approval wiring for the SDLC agent.

Two pieces live here:

1. ``INTERRUPT_ON`` + ``approval_description`` — the config passed to
   ``create_deep_agent(interrupt_on=...)`` so the agent pauses for human
   approval before ``write_file`` / ``edit_file`` runs. deepagents appends the
   stock ``HumanInTheLoopMiddleware`` when this is set, and declarative
   subagents inherit it, so writes inside subagents are gated too.

2. ``ShellGuardMiddleware`` — a deterministic safety guard (NOT a human prompt)
   that hard-blocks destructive ``execute`` (shell) commands before they reach
   the sandbox. It lives in middleware, so it only ever sees the *agent's* tool
   calls — the server's own infrastructure shell (workspace init, OKF
   bookkeeping) goes straight through ``DockerBackend.execute`` untouched.

Tool names are the deepagents filesystem-middleware names: ``write_file``,
``edit_file`` (args ``file_path`` / ``content`` / ``old_string`` /
``new_string``) and ``execute`` (arg ``command``).
"""

from __future__ import annotations

import logging
import re
import shlex
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain.agents.middleware.types import AgentMiddleware

logger = logging.getLogger(__name__)

# ── Approval gating (HumanInTheLoopMiddleware config) ─────────────────────

_PREVIEW_LEN = 600


def approval_description(tool_call: Any, state: Any, runtime: Any) -> str:
    """Render a human-readable description of a write/edit awaiting approval.

    Used as the ``description`` factory in the ``interrupt_on`` config so the
    frontend approval card has good text even before it parses the raw args.
    """
    name = tool_call.get("name", "?")
    args = tool_call.get("args", {}) or {}
    path = args.get("file_path", "?")

    if name == "edit_file":
        old = (args.get("old_string") or "")[:_PREVIEW_LEN]
        new = (args.get("new_string") or "")[:_PREVIEW_LEN]
        return f"edit_file → {path}\n\n- old:\n{old}\n\n+ new:\n{new}"

    content = (args.get("content") or "")[:_PREVIEW_LEN]
    return f"{name} → {path}\n\n{content}"


# The decision set is fixed for v1: approve / reject / edit (no "respond").
INTERRUPT_ON: dict[str, Any] = {
    "write_file": {
        "allowed_decisions": ["approve", "reject", "edit"],
        "description": approval_description,
    },
    "edit_file": {
        "allowed_decisions": ["approve", "reject", "edit"],
        "description": approval_description,
    },
}


# ── Destructive-shell guard ───────────────────────────────────────────────

# Targets that make a recursive/forced delete catastrophic. A deep workspace
# subpath (e.g. /workspace/project_x/tmp) is intentionally NOT in this set —
# agents legitimately clean up scratch dirs.
_RM_DANGER_TARGETS = {
    "/", "/*", "~", "~/", "~/*", "*", ".", "./*", "$HOME", "$HOME/*",
    "/workspace", "/workspace/", "/workspace/*",
    "/etc", "/var", "/usr", "/bin", "/sbin", "/lib", "/boot",
    "/root", "/home", "/dev", "/opt", "/sys", "/proc",
}

# Non-rm destructive patterns (regex, matched case-insensitively against the
# raw command string). Each entry: (compiled regex, human reason).
_DESTRUCTIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bmkfs(\.\w+)?\b"), "filesystem format (mkfs)"),
    (re.compile(r"\bwipefs\b"), "filesystem signature wipe (wipefs)"),
    (re.compile(r"\bdd\b[^\n]*\bof=", re.IGNORECASE), "raw disk write (dd of=)"),
    (re.compile(r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"), "fork bomb"),
    (re.compile(r">\s*/dev/(sd|nvme|hd|disk|mmcblk)", re.IGNORECASE), "redirect to block device"),
    (re.compile(r"\bchmod\b\s+-[a-zA-Z]*R[a-zA-Z]*\s+[0-7]{3,4}\s+/\s*(\s|$)"), "recursive chmod on /"),
    (re.compile(r"\bshred\b"), "secure file shredding (shred)"),
    (re.compile(r"\bfdisk\b|\bparted\b"), "disk partitioning"),
    (re.compile(r"\bfind\s+(/|~|\$HOME)\S*\s[^\n]*-delete"), "recursive find -delete on a root path"),
]


def _rm_is_destructive(tokens: list[str]) -> bool:
    """True if the token list contains an ``rm`` with recursive+force on a
    dangerous target (root, home, wildcard, or the workspace root itself)."""
    for i, tok in enumerate(tokens):
        if tok != "rm" and not tok.endswith("/rm"):
            continue
        rest = tokens[i + 1 :]
        flags = "".join(t[1:] for t in rest if t.startswith("-") and not t.startswith("--"))
        recursive = "r" in flags or "R" in flags or "--recursive" in rest
        forced = "f" in flags or "--force" in rest
        if not (recursive and forced):
            continue
        targets = [t for t in rest if not t.startswith("-")]
        # A bare `rm -rf` with no explicit target, or any dangerous target.
        if not targets:
            return True
        for t in targets:
            if t in _RM_DANGER_TARGETS:
                return True
    return False


def is_destructive_command(command: str) -> str | None:
    """Return a reason string if *command* is destructive, else ``None``.

    Splits on shell separators so a destructive sub-command inside a chained
    command (``foo && rm -rf /``) is still caught.
    """
    if not command:
        return None

    for pattern, reason in _DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            return reason

    # Tokenize each chained segment and inspect rm usage.
    for segment in re.split(r"&&|\|\||;|\|", command):
        segment = segment.strip()
        if not segment:
            continue
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        if _rm_is_destructive(tokens):
            return "recursive forced delete (rm -rf) on a protected path"

    return None


class ShellGuardMiddleware(AgentMiddleware):
    """Deterministically block destructive ``execute`` (shell) tool calls.

    Mirrors ``HumanInTheLoopMiddleware``'s rewrite pattern: it drops the
    offending tool call from the AI message and appends an error
    ``ToolMessage`` so the model learns the command was refused and can adapt.
    No human prompt — destructive shell is never allowed, regardless of the
    auto-approve setting.
    """

    def after_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        messages = state["messages"]
        if not messages:
            return None
        last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
        if not last_ai or not last_ai.tool_calls:
            return None

        kept: list[Any] = []
        blocked_msgs: list[ToolMessage] = []
        changed = False

        for tool_call in last_ai.tool_calls:
            if tool_call.get("name") == "execute":
                command = (tool_call.get("args") or {}).get("command", "")
                reason = is_destructive_command(command)
                if reason:
                    changed = True
                    logger.warning(
                        "ShellGuard blocked destructive command (%s): %r", reason, command
                    )
                    blocked_msgs.append(
                        ToolMessage(
                            content=(
                                f"BLOCKED: refused to run a destructive shell command "
                                f"({reason}). Command: {command!r}. This safety guard "
                                f"cannot be overridden. Choose a non-destructive approach "
                                f"(e.g. target a specific file/subdirectory)."
                            ),
                            name="execute",
                            tool_call_id=tool_call["id"],
                            status="error",
                        )
                    )
                    continue
            kept.append(tool_call)

        if not changed:
            return None

        last_ai.tool_calls = kept
        return {"messages": [last_ai, *blocked_msgs]}

    async def aafter_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return self.after_model(state, runtime)
