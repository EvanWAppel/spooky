"""Tests for the corrective logline rewrite pass (Group F follow-up).

The rewrite step takes an existing ``ai-drafted`` logline plus its triage
critique and produces a better draft. It obeys the same hard rules as the
first draft (≤30 words, no verbatim run of more than 8 words), keeps
``review_status: "ai-drafted"`` for the owner's later review, and never
touches a ``human-reviewed`` record.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from build.loglines import LoglineError
from build.rewrite import rewrite_all, rewrite_logline

GOOD = (
    "Mulder tracks a bile-hoarding mutant nesting behind Baltimore walls "
    "as Scully doubts the pattern."
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
        "logline_generated": "A stretchy man eats livers every thirty years.",
        "logline": None,
        "review_status": "ai-drafted",
        "reviewed_at": None,
        "review_note": None,
    }
    return {**base, **overrides}


def test_rewrite_returns_a_capped_logline() -> None:
    client = StubClient([GOOD])

    text = rewrite_logline(client, _record(), sources=[], critique="too vague")

    assert text == GOOD
    assert len(text.split()) <= 30
    assert len(client.calls) == 1


def test_rewrite_feeds_the_critique_and_prior_draft_to_the_model() -> None:
    client = StubClient([GOOD])
    record = _record(logline_generated="A stretchy man eats livers.")

    rewrite_logline(
        client, record, sources=[], critique="No liver-eating; he hoards bile."
    )

    prompt = client.calls[0]["messages"][0]["content"]
    assert "No liver-eating; he hoards bile." in prompt
    assert "A stretchy man eats livers." in prompt


def test_rewrite_retries_when_over_the_word_cap() -> None:
    client = StubClient([LONG, GOOD])

    text = rewrite_logline(client, _record(), sources=[], critique="tighten it")

    assert text == GOOD
    assert len(client.calls) == 2


def test_rewrite_raises_after_exhausted_retries() -> None:
    client = StubClient([LONG, LONG, LONG])

    with pytest.raises(LoglineError, match="s01e03"):
        rewrite_logline(client, _record(), sources=[], critique="x", retries=3)


def test_rewrite_all_updates_the_draft_and_keeps_ai_drafted(tmp_path: Path) -> None:
    episodes = tmp_path / "episodes"
    episodes.mkdir()
    (episodes / "s01e03.json").write_text(json.dumps(_record()))
    triage = {"s01e03": {"grade": "C", "critique": "invents the eating detail"}}
    client = StubClient([GOOD])

    written, failures = rewrite_all(client, episodes, sections={}, triage=triage)

    assert (written, failures) == (1, [])
    record = json.loads((episodes / "s01e03.json").read_text())
    assert record["logline_generated"] == GOOD
    assert record["review_status"] == "ai-drafted"
    assert record["logline"] is None  # still never machine-written


def test_rewrite_all_never_touches_human_reviewed_records(tmp_path: Path) -> None:
    episodes = tmp_path / "episodes"
    episodes.mkdir()
    reviewed = _record(
        logline="Evan's approved logline.",
        review_status="human-reviewed",
        reviewed_at="2026-07-27T00:00:00Z",
    )
    (episodes / "s01e03.json").write_text(json.dumps(reviewed))
    triage = {"s01e03": {"grade": "C", "critique": "would change it"}}
    client = StubClient([])  # any API call blows up the stub

    written, failures = rewrite_all(client, episodes, sections={}, triage=triage)

    assert (written, failures) == (0, [])
    assert json.loads((episodes / "s01e03.json").read_text()) == reviewed
    assert client.calls == []


def test_rewrite_all_skips_records_without_a_draft(tmp_path: Path) -> None:
    episodes = tmp_path / "episodes"
    episodes.mkdir()
    (episodes / "s01e03.json").write_text(json.dumps(_record(logline_generated=None)))
    client = StubClient([])

    written, failures = rewrite_all(client, episodes, sections={}, triage={})

    assert (written, failures) == (0, [])
    assert client.calls == []


def test_rewrite_all_records_a_refusal_and_keeps_going(tmp_path: Path) -> None:
    """A deterministic refusal (the base64-titled s11e07) must not abort the
    batch — it is reported as a failure and its prior draft is left intact,
    while the other records still get rewritten."""
    episodes = tmp_path / "episodes"
    episodes.mkdir()
    refused = _record(id="s11e07", title="Rm9sbG93ZXJz", logline_generated="keep me")
    ok = _record(id="s01e03")
    (episodes / "s11e07.json").write_text(json.dumps(refused))
    (episodes / "s01e03.json").write_text(json.dumps(ok))

    class MixedClient(StubClient):
        def _create(self, **kwargs):
            self.calls.append(kwargs)
            # s01e03 gets a clean reply; the base64-titled record is refused.
            if "Rm9sbG93ZXJz" in kwargs["messages"][0]["content"]:
                return SimpleNamespace(content=[], stop_reason="refusal")
            return SimpleNamespace(content=[SimpleNamespace(text=GOOD)])

    written, failures = rewrite_all(MixedClient([]), episodes, sections={}, triage={})

    assert written == 1
    assert failures == ["s11e07"]
    assert (
        json.loads((episodes / "s11e07.json").read_text())["logline_generated"]
        == "keep me"
    )
