"""Tests for the logline drafting step (TASKS F-01, F-02).

Loglines are ≤30 words, original wording (no verbatim run of more than
8 words from any source text), machine-owned (`logline_generated`), and
never touch `logline` or human-reviewed records.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from build.loglines import (
    LoglineError,
    contains_verbatim_run,
    draft_logline,
    generate_all,
)

GOOD = (
    "Mulder chases a shape-shifting predator through Baltimore crawlspaces "
    "while Scully weighs the evidence."
)
LONG = " ".join(["word"] * 31)


class StubClient:
    """Duck-typed stand-in for anthropic.Anthropic — records every call."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._replies:
            raise AssertionError("stub exhausted")
        text = self._replies.pop(0)
        return SimpleNamespace(content=[SimpleNamespace(text=text)])


def _record(**overrides) -> dict:
    base = {
        "id": "s01e03",
        "title": "Squeeze",
        "season": 1,
        "episode": 3,
        "air_date": "1993-09-24",
        "label_derived": "monster-of-the-week",
        "director": ["Harry Longstreet"],
        "writers": ["Glen Morgan", "James Wong"],
        "guest_cast": ["Doug Hutchison"],
        "logline_generated": None,
        "logline": None,
        "review_status": "unreviewed",
        "reviewed_at": None,
        "review_note": None,
    }
    return {**base, **overrides}


def test_draft_returns_a_capped_logline() -> None:
    client = StubClient([GOOD])

    text = draft_logline(client, _record(), sources=[])

    assert text == GOOD
    assert len(text.split()) <= 30
    assert len(client.calls) == 1


def test_draft_skips_non_text_blocks_in_the_response() -> None:
    """Found live: the model returns a thinking block before the text block,
    so content[0] is not the logline."""

    class ThinkingFirstClient(StubClient):
        def _create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                content=[
                    SimpleNamespace(thinking="pondering the paranormal"),
                    SimpleNamespace(text=GOOD),
                ]
            )

    text = draft_logline(ThinkingFirstClient([]), _record(), sources=[])

    assert text == GOOD


def test_draft_retries_when_over_the_word_cap() -> None:
    client = StubClient([LONG, GOOD])

    text = draft_logline(client, _record(), sources=[])

    assert text == GOOD
    assert len(client.calls) == 2


def test_draft_retries_when_copying_the_source_verbatim() -> None:
    source = (
        "The writers based the character on a persistent urban legend about "
        "a man who lives inside the walls of old buildings."
    )
    plagiarized = "A man who lives inside the walls of old buildings is hunted by Mulder."

    client = StubClient([plagiarized, GOOD])
    text = draft_logline(client, _record(), sources=[source])

    assert text == GOOD
    assert len(client.calls) == 2


def test_draft_raises_after_exhausted_retries() -> None:
    client = StubClient([LONG, LONG, LONG])

    with pytest.raises(LoglineError, match="s01e03"):
        draft_logline(client, _record(), sources=[], retries=3)


def test_contains_verbatim_run_is_word_based_and_case_insensitive() -> None:
    """F-01: runs of MORE than 8 words trip the guard; exactly 8 is allowed."""
    source = "one two three four five six seven eight nine ten"

    # 9 shared words, despite case and punctuation differences -> trips.
    assert contains_verbatim_run(
        "start ONE two, three four FIVE six seven eight nine end", [source]
    )
    # Exactly 8 shared words -> allowed.
    assert not contains_verbatim_run(
        "one two three four five six seven eight other words", [source]
    )


def test_generate_all_writes_drafts_and_sets_ai_drafted(tmp_path: Path) -> None:
    episodes = tmp_path / "episodes"
    episodes.mkdir()
    (episodes / "s01e03.json").write_text(json.dumps(_record()))
    client = StubClient([GOOD])

    generate_all(client, episodes, sections={})

    written = json.loads((episodes / "s01e03.json").read_text())
    assert written["logline_generated"] == GOOD
    assert written["review_status"] == "ai-drafted"
    assert written["logline"] is None  # never written by the machine


def test_generate_all_never_touches_human_reviewed_records(tmp_path: Path) -> None:
    """F-06 groundwork: regeneration must not even call the API for a
    reviewed record, let alone change it."""
    episodes = tmp_path / "episodes"
    episodes.mkdir()
    reviewed = _record(
        logline="Evan's approved logline.",
        logline_generated="an old draft",
        review_status="human-reviewed",
        reviewed_at="2026-07-27T00:00:00Z",
    )
    (episodes / "s01e03.json").write_text(json.dumps(reviewed))
    client = StubClient([])  # any API call would blow up the stub

    generate_all(client, episodes, sections={})

    unchanged = json.loads((episodes / "s01e03.json").read_text())
    assert unchanged == reviewed
    assert client.calls == []
