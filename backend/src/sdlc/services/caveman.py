"""Caveman, natively: make the agent read less without adding a dependency.

Measured on a real trial before this existed: 6,224,330 input tokens against
364,631 output, p95 63k input per model call. Nearly all of it is *tool
results* — file reads, shell output, validator reports, subagent hand-offs —
accumulating in the message list until the next call resends them.

The measurement part of this module lives in `services/usage.py` (nothing here
serves a cache; providers do that). This module is the other half: shrink what
comes back from a tool before it enters the model context, so those results are
never billed at full length in the first place.

Upstream this idea is Caveman's "read less" runtime (github.com/JuliusBrussee/
caveman, Apache-2.0). Its engine is a separate Go process the Python client
talks to over HTTP; this is a native port of the contract we can honour without
a sidecar, and it deliberately keeps the same guarantees:

  * **Deterministic.** Format routing and compression are pure functions of the
    bytes. Nothing calls a model. That matters for the cache work in
    `services/usage.py`: a non-deterministic rewrite of a tool result would
    change the prefix on every turn and cost more than it saves.
  * **Errors stay verbatim.** Validation is this pipeline's product. A compacted
    OpenAPI report that drops findings would make an agent claim a clean run it
    never had, so any line that looks like an error, warning or failure is kept
    at full length, whatever the format.
  * **The original is kept.** Bytes are stored before the shortened view
    replaces them; every compacted result carries its handle, and the
    `caveman_retrieve` tool pages the exact text back. If the store write
    fails, nothing is shortened — same rule as upstream.

What this module never touches: agent-written artifacts, prompts, and tool
inputs. Only tool *results* on their way into context. Work that has to survive
is a file on disk, written by the agent, not a chat message.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from sdlc.core.config import (
    CAVEMAN_MIN_CHARS,
    CAVEMAN_MODE,
    CAVEMAN_STORE_DIR,
    CAVEMAN_STORE_MAX,
)

logger = logging.getLogger(__name__)

# Tool results that must never be rewritten: recovery itself, and the
# clarifying-question tool whose payload the UI parses.
_EXEMPT_TOOLS = frozenset({"caveman_retrieve", "ask_question"})

# A line carrying one of these is a finding, not prose. Kept whole.
_FINDING_RE = re.compile(
    r"error|warn|fail|exception|traceback|fatal|conflict|invalid|denied|"
    r"mismatch|missing|unexpected|✗|❌|\bE\d{3}\b",
    re.IGNORECASE,
)

# Hard ceilings. A tool result bigger than this is a bug upstream (the
# filesystem middleware offloads instead); we still bound our own work.
_MAX_INPUT_CHARS = 4_000_000


def enabled() -> bool:
    """Whether tool results are compacted at all."""
    return (CAVEMAN_MODE or "").strip().lower() not in ("", "off", "0", "false", "none")


# ── Format detection ─────────────────────────────────────────────────────

JSON = "json"
DIFF = "diff"
HTML = "html"
TABLE = "table"
LOG = "log"
TEXT = "text"


def detect_format(text: str) -> str:
    """Classify a payload by its bytes. No model, no heuristics that can drift.

    Order matters: JSON is unambiguous, a diff announces itself with hunk
    headers, and only then do the softer shapes get a vote. A misdetection is
    not fatal — every compressor degrades to a bounded head/tail view — but it
    does change what gets kept, so the cheap certain cases come first.
    """
    head = text.lstrip()[:400]
    if head[:1] in ("{", "[") and len(text) > 2:
        try:
            json.loads(text)
            return JSON
        except (ValueError, TypeError):
            pass
    if "@@ " in text[:4000] or text.startswith("diff --git "):
        return DIFF
    lowered = head.lower()
    if lowered.startswith(("<!doctype html", "<html")) or "<div" in lowered[:200]:
        return HTML
    lines = text.splitlines()
    if len(lines) > 3 and _looks_tabular(lines):
        return TABLE
    if len(lines) > 8 and _looks_like_log(lines):
        return LOG
    return TEXT


def _looks_tabular(lines: list[str]) -> bool:
    """True when most lines split into the same number of fields."""
    sample = [ln for ln in lines[:40] if ln.strip()]
    if len(sample) < 3:
        return False
    for sep in (",", "\t", "|", ";"):
        counts = Counter(ln.count(sep) for ln in sample)
        common, n = counts.most_common(1)[0]
        if common >= 2 and n >= len(sample) * 0.8:
            return True
    return False


def _looks_like_log(lines: list[str]) -> bool:
    """Timestamps or level markers on a useful share of lines."""
    marker = re.compile(
        r"^\s*(\d{2,4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}|\[[A-Z]+\]|"
        r"(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL)\b|\w+:\d+:)"
    )
    hits = sum(1 for ln in lines[:60] if marker.search(ln))
    return hits >= max(3, len(lines[:60]) // 4)


# ── Compressors ──────────────────────────────────────────────────────────


def _short_str(value: str, limit: int = 240) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}… ({len(value)} chars)"


def _json_view(value: Any, depth: int = 0, max_items: int = 3) -> Any:
    """Keep the shape of a JSON payload, not every leaf.

    Validator reports are lists of findings: the agent needs to know there are
    240 of them and what the first few say, not to read all 240 twice.
    """
    if isinstance(value, str):
        # A finding string is payload: never abbreviate it.
        if _FINDING_RE.search(value):
            return value
        return _short_str(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if depth >= 3:
        if isinstance(value, dict):
            return f"<object: {len(value)} keys>"
        return f"<array: {len(value)} items>"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, list) and len(item) > max_items:
                out[key] = [_json_view(v, depth + 1, max_items) for v in item[:max_items]]
                out[key].append(f"… {len(item) - max_items} more")
            else:
                out[key] = _json_view(item, depth + 1, max_items)
        return out
    if isinstance(value, list):
        shown = [_json_view(v, depth + 1, max_items) for v in value[:max_items]]
        if len(value) > max_items:
            shown.append(f"… {len(value) - max_items} more")
        return shown
    return _short_str(str(value))


def _compact_json(text: str) -> str:
    payload = json.loads(text)
    view = _json_view(payload)
    if isinstance(payload, list):
        shape = f"array[{len(payload)}]"
    elif isinstance(payload, dict):
        shape = f"object[{len(payload)} keys]"
    else:
        shape = type(payload).__name__
    body = json.dumps(view, indent=1, ensure_ascii=False, default=str)
    return f"// {shape}, compacted view\n{body}"


def _compact_diff(text: str) -> str:
    """Keep hunks, changed lines and file headers. Drop unchanged context."""
    kept: list[str] = []
    dropped = 0
    for line in text.splitlines():
        if line.startswith(("@@", "+++", "---", "diff ", "index ", "new file", "deleted file")):
            kept.append(line)
        elif line[:1] in ("+", "-"):
            kept.append(line)
        elif _FINDING_RE.search(line):
            kept.append(line)
        else:
            dropped += 1
    if dropped:
        kept.append(f"… {dropped} unchanged context lines dropped")
    return "\n".join(kept[:400])


def _compact_html(text: str) -> str:
    body = re.sub(r"(?is)<(script|style|svg)[^>]*>.*?</\1>", " ", text)
    body = re.sub(r"(?s)<[^>]+>", " ", body)
    body = re.sub(r"[ \t\r\f\v]+", " ", body)
    body = re.sub(r"\n\s*\n+", "\n", body).strip()
    return _head_tail(body.splitlines(), head=80, tail=10, unit="lines")


def _compact_table(text: str) -> str:
    """Header, a sample of rows, and the true shape."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return text
    findings = [ln for ln in lines[1:] if _FINDING_RE.search(ln)]
    head = lines[:6]
    tail = lines[-2:] if len(lines) > 8 else []
    out = list(head)
    if findings:
        out.extend(findings[:15])
        if len(findings) > 15:
            out.append(f"… {len(findings) - 15} more rows mentioning a finding")
    if tail:
        out.append(f"… {len(lines) - len(head) - len(tail)} rows omitted")
        out.extend(tail)
    return "\n".join(out)


def _compact_log(text: str) -> str:
    """Every finding line, deduplicated, plus the head and tail of the run."""
    deduped: list[str] = []
    repeat = 1
    for line in text.splitlines():
        if line.strip() and deduped and line == deduped[-1]:
            repeat += 1
            continue
        if repeat > 1:
            deduped[-1] = f"{deduped[-1]}  (x{repeat})"
            repeat = 1
        deduped.append(line)
    if repeat > 1:
        deduped[-1] = f"{deduped[-1]}  (x{repeat})"

    findings = [ln for ln in deduped if _FINDING_RE.search(ln)]
    head = deduped[:15]
    tail = deduped[-12:]
    out: list[str] = []
    out.extend(head)
    if len(findings) > 40:
        out.extend(findings[:40])
        out.append(f"… {len(findings) - 40} more lines mention a finding")
    else:
        for line in findings:
            if line not in out:
                out.append(line)
    for line in tail:
        if line not in out:
            out.append(line)
    omitted = len(deduped) - len(out)
    if omitted > 0:
        out.insert(min(len(head), len(out)), f"… {omitted} lines omitted")
    return "\n".join(out)


def _compact_text(text: str) -> str:
    return _head_tail(text.splitlines(), head=70, tail=20, unit="lines")


def _head_tail(lines: list[str], head: int, tail: int, unit: str) -> str:
    if len(lines) <= head + tail:
        return "\n".join(lines)
    findings = [ln for ln in lines[head:-tail] if _FINDING_RE.search(ln)]
    out = list(lines[:head])
    if findings:
        out.extend(findings[:20])
        if len(findings) > 20:
            out.append(f"… {len(findings) - 20} more lines mention a finding")
    out.append(f"… {len(lines) - head - tail} {unit} omitted")
    out.extend(lines[-tail:])
    return "\n".join(out)


_COMPRESSORS: dict[str, Callable[[str], str]] = {
    JSON: _compact_json,
    DIFF: _compact_diff,
    HTML: _compact_html,
    TABLE: _compact_table,
    LOG: _compact_log,
    TEXT: _compact_text,
}


# ── Original store ───────────────────────────────────────────────────────


def _store_root() -> Path:
    return Path(CAVEMAN_STORE_DIR)


def _prune(root: Path) -> None:
    """Evict the oldest originals once the store exceeds its cap.

    Best effort on purpose: failing to prune must never fail the write that
    just succeeded, so an unlink error is swallowed rather than propagated.
    """
    limit = max(1, CAVEMAN_STORE_MAX)
    try:
        files = sorted(root.glob("*.txt"), key=lambda p: p.stat().st_mtime)
    except OSError:
        return
    for stale in files[: max(0, len(files) - limit)]:
        try:
            stale.unlink()
        except OSError:
            pass


def store_original(text: str) -> str | None:
    """Persist the exact bytes and return the handle, or None if that failed.

    The handle is content-addressed, so the same payload always maps to the
    same file: repeated tool calls cost one write, and a retrieve is stable
    across turns.
    """
    try:
        root = _store_root()
        root.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(text.encode("utf-8", "surrogatepass")).hexdigest()[:16]
        path = root / f"{digest}.txt"
        if not path.exists():
            path.write_text(text, encoding="utf-8", errors="surrogatepass")
            _prune(root)
        return digest
    except OSError as exc:
        logger.warning("caveman: could not store original (%s); not compacting", exc)
        return None


def load_original(handle: str, offset: int = 0, limit: int = 6000) -> str:
    """Read a stored original by handle. Bounded, so paging cannot flood."""
    safe = re.sub(r"[^0-9a-f]", "", handle or "")[:16]
    if not safe:
        return "caveman_retrieve: invalid handle"
    path = _store_root() / f"{safe}.txt"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return f"caveman_retrieve: no stored original for handle {safe!r} (expired or unknown)"
    limit = max(500, min(int(limit), 20_000))
    offset = max(0, int(offset))
    chunk = text[offset : offset + limit]
    end = offset + len(chunk)
    footer = "" if end >= len(text) else f"\n… [{end}/{len(text)} chars; continue with offset={end}]"
    return chunk + footer


# ── Compaction ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Compaction:
    text: str
    fmt: str
    original_chars: int

    @property
    def kept_chars(self) -> int:
        return len(self.text)

    @property
    def changed(self) -> bool:
        return self.fmt != "none"


def compact(text: str, *, store: bool = True) -> Compaction:
    """Shorten a tool result. Pure apart from the optional original write.

    Returns the text unchanged (`fmt == "none"`) whenever compacting would not
    pay: below the floor, no net gain, an unknown shape, or a failed store.
    Several of those are deliberate refusals rather than best-effort edits.
    """
    if not enabled() or not text or len(text) < CAVEMAN_MIN_CHARS:
        return Compaction(text, "none", len(text))

    # Bound our own work, not the archive: what is stored stays exact, so a
    # pathological payload is still recoverable in full.
    work = text[:_MAX_INPUT_CHARS]

    fmt = detect_format(work)
    try:
        shortened = _COMPRESSORS[fmt](work)
    except Exception as exc:  # noqa: BLE001 - a compressor must never break a tool
        logger.debug("caveman: %s compressor failed (%s); passing through", fmt, exc)
        return Compaction(text, "none", len(text))

    # Under 30% saved is not worth the risk of hiding something: the agent
    # would pay the footer and the retrieve round-trip for nearly nothing.
    if len(shortened) > len(work) * 0.7:
        return Compaction(text, "none", len(text))

    if store:
        handle = store_original(text)
        if handle is None:
            return Compaction(text, "none", len(text))
        shortened = (
            f"{shortened}\n\n[caveman {fmt}: {len(text)}→{len(shortened)} chars. "
            f'Full original: caveman_retrieve("{handle}")]'
        )
    return Compaction(shortened, fmt, len(text))


# ── Measurement ──────────────────────────────────────────────────────────


class CavemanStats:
    """Process-local tally, surfaced next to the usage ledger per run."""

    results_compacted: int = 0
    chars_before: int = 0
    chars_after: int = 0
    by_format: Counter = Counter()

    @classmethod
    def record(cls, compaction: Compaction) -> None:
        if not compaction.changed:
            return
        cls.results_compacted += 1
        cls.chars_before += compaction.original_chars
        cls.chars_after += compaction.kept_chars
        cls.by_format[compaction.fmt] += 1

    @classmethod
    def snapshot(cls) -> dict[str, Any]:
        saved = max(0, cls.chars_before - cls.chars_after)
        ratio = saved / cls.chars_before if cls.chars_before else 0.0
        return {
            "results_compacted": cls.results_compacted,
            "chars_before": cls.chars_before,
            "chars_after": cls.chars_after,
            "chars_saved": saved,
            "saved_ratio": ratio,
            "by_format": dict(cls.by_format),
        }

    @classmethod
    def reset(cls) -> None:
        cls.results_compacted = 0
        cls.chars_before = 0
        cls.chars_after = 0
        cls.by_format = Counter()


# ── Middleware ───────────────────────────────────────────────────────────


def _shrink(result: Any, request: Any) -> Any:
    """Compact a tool result in place, leaving anything unexpected alone."""
    if not enabled() or not isinstance(result, ToolMessage):
        return result
    call = getattr(request, "tool_call", None) or {}
    if call.get("name") in _EXEMPT_TOOLS:
        return result
    content = getattr(result, "content", None)
    if not isinstance(content, str):
        # Multimodal or block content: not our shape to rewrite.
        return result
    compaction = compact(content)
    if not compaction.changed:
        return result
    CavemanStats.record(compaction)
    return result.model_copy(update={"content": compaction.text})


class CavemanToolMiddleware(AgentMiddleware):
    """Caveman "read less" at the tool boundary.

    Sits where every tool result passes on its way into the message list, so
    the orchestrator and all seven subagents share one implementation, and a
    future tool is covered the day it is registered — no per-call-site wiring.
    """

    def wrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        return _shrink(handler(request), request)

    async def awrap_tool_call(
        self, request: Any, handler: Callable[[Any], Any]
    ) -> Any:
        return _shrink(await handler(request), request)


def caveman_middleware() -> list[Any]:
    """The middleware list to splice into an agent, empty when disabled."""
    return [CavemanToolMiddleware()] if enabled() else []


# ── Recovery tool ────────────────────────────────────────────────────────


class _RetrieveArgs(BaseModel):
    handle: str = Field(description="Handle printed in the [caveman ...] footer.")
    offset: int = Field(default=0, description="Character offset to start from.")
    limit: int = Field(default=6000, description="Max characters to return (500-20000).")


class CavemanRetrieveTool(BaseTool):
    """Page back the exact bytes a compacted tool result replaced."""

    name: str = "caveman_retrieve"
    description: str = (
        "Read the full original of a compacted tool result. Every result that "
        "was shortened ends with a [caveman ...] footer naming a handle; pass "
        "that handle here, and page with offset/limit if the output is long. "
        "Use it whenever the shortened view looks like it hid a detail you "
        "need — never guess a value you could retrieve."
    )
    args_schema: type[BaseModel] = _RetrieveArgs

    def _run(
        self, handle: str, offset: int = 0, limit: int = 6000, **kwargs: Any
    ) -> str:
        return load_original(handle, offset=offset, limit=limit)


def recovery_tools() -> list[Any]:
    """The retrieve tool, for every agent that can receive a shortened result.

    Recovery is plumbing rather than a domain capability, so it is attached to
    all agents and the orchestrator rather than to a chosen few: an agent that
    gets a compacted result without a way to read it back would have to guess.
    """
    return [CavemanRetrieveTool()] if enabled() else []

