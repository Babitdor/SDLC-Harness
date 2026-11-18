"""Tests for the inline <think>…</think> stream splitter.

Reasoning models served through OpenAI-compatible gateways without a reasoning
parser emit chain-of-thought as ``<think>…</think>`` inline in the content.
``_split_think`` peels that out of the visible answer into the reasoning
channel — even when the tags are split across streaming chunks.
"""

from __future__ import annotations

from sdlc.api.app import _partial_suffix_len, _split_think


def _run(deltas: list[str]) -> tuple[str, str]:
    """Feed deltas through _split_think sequentially, return (visible, reasoning)."""
    state: dict = {"in_think": False, "buf": ""}
    vis, rea = [], []
    for d in deltas:
        v, r = _split_think(d, state)
        vis.append(v)
        rea.append(r)
    # Flush any held-back tail (mirrors the stream-end flush in app.py).
    if state["buf"]:
        (rea if state["in_think"] else vis).append(state["buf"])
    return "".join(vis), "".join(rea)


def test_plain_content_passes_through():
    vis, rea = _run(["Hello ", "world."])
    assert vis == "Hello world."
    assert rea == ""


def test_single_delta_think_block():
    vis, rea = _run(["<think>weighing options</think>The answer is 42."])
    assert vis == "The answer is 42."
    assert rea == "weighing options"


def test_think_before_and_after_visible():
    vis, rea = _run(["intro <think>hmm</think> outro"])
    assert vis == "intro  outro"
    assert rea == "hmm"


def test_open_tag_split_across_chunks():
    # The "<thi" | "nk>" boundary must not be emitted as visible text.
    vis, rea = _run(["answer <thi", "nk>secret</think> done"])
    assert "<think>" not in vis
    assert "secret" not in vis
    assert vis == "answer  done"
    assert rea == "secret"


def test_close_tag_split_across_chunks():
    vis, rea = _run(["<think>reason", "ing</thi", "nk>visible"])
    assert vis == "visible"
    assert rea == "reasoning"


def test_unterminated_think_flushes_as_reasoning():
    vis, rea = _run(["<think>still thinking when the stream ended"])
    assert vis == ""
    assert rea == "still thinking when the stream ended"


def test_partial_suffix_len():
    assert _partial_suffix_len("abc<thi", "<think>") == 4   # "<thi"
    assert _partial_suffix_len("abc<", "<think>") == 1       # "<"
    assert _partial_suffix_len("abcdef", "<think>") == 0     # no overlap
    # A complete tag is a full match, not a partial suffix (len-1 cap).
    assert _partial_suffix_len("<think>", "<think>") == 0
