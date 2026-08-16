"""Tests for the logline triage pass (review accelerator).

Triage grades every not-yet-human-reviewed draft A/B/C with a one-line
critique, writing a separate ``data/logline_triage.json`` artifact. It is
a *read-only* pass over the records — it never writes an episode file and
never touches a sacred (``human-reviewed``) field. Its only job is to tell
the owner where to spend attention.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.triage import (
    TriageError,
    grade_all,
    grade_record,
    load_triage,
    parse_verdict,
)


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
        "logline_generated": "A killer who squeezes through impossible gaps.",
        "logline": None,
        "review_status": "ai-drafted",
        "reviewed_at": None,
        "review_note": None,
    }
    return {**base, **overrides}


@pytest.fixture
def episodes_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "episodes"
    directory.mkdir()
    (directory / "s01e03.json").write_text(json.dumps(_record()))
    (directory / "s01e04.json").write_text(
        json.dumps(_record(id="s01e04", title="Conduit"))
    )
    (directory / "s01e05.json").write_text(
        json.dumps(
            _record(
                id="s01e05",
                title="The Jersey Devil",
                logline="Already reviewed.",
                review_status="human-reviewed",
            )
        )
    )
    return directory


def test_parse_verdict_splits_grade_from_critique() -> None:
    assert parse_verdict("A: accurate and specific, ship it") == (
        "A",
        "accurate and specific, ship it",
    )


def test_parse_verdict_is_case_insensitive_on_grade() -> None:
    grade, _ = parse_verdict("b - generic ending")
    assert grade == "B"


def test_parse_verdict_rejects_an_unknown_grade() -> None:
    """A grade outside A/B/C is a model error we surface, never swallow."""
    with pytest.raises(TriageError, match="grade"):
        parse_verdict("Z: this is not a real grade")


class RefusingClient:
    """The model returns a hard refusal (empty content, stop_reason=refusal)
    — the real behaviour on s11e07, whose title is the base64 token
    ``Rm9sbG93ZXJz`` that trips a safety classifier."""

    def __init__(self) -> None:
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **_kwargs):
        self.calls += 1
        return SimpleNamespace(content=[], stop_reason="refusal")


def test_grade_record_fails_fast_on_a_refusal() -> None:
    """A refusal is deterministic — retrying wastes calls. Surface it clearly
    and immediately, don't dress it up as a budget problem."""
    client = RefusingClient()

    with pytest.raises(TriageError, match="refus"):
        grade_record(client, _record())

    assert client.calls == 1  # no pointless retries


def test_grade_record_returns_id_grade_and_critique() -> None:
    client = StubClient(["C: invents a virus detail not in the credits"])

    verdict = grade_record(client, _record())

    assert verdict["id"] == "s01e03"
    assert verdict["grade"] == "C"
    assert verdict["critique"] == "invents a virus detail not in the credits"
    # The draft itself must be in the prompt — that is what is being judged.
    sent = client.calls[0]["messages"][0]["content"]
    assert "squeezes through impossible gaps" in sent


def test_grade_all_skips_human_reviewed_records(episodes_dir: Path) -> None:
    client = StubClient(["A: good", "B: fine"])
    out = episodes_dir.parent / "logline_triage.json"

    grade_all(client, episodes_dir, out)

    triage = load_triage(out)
    assert set(triage) == {"s01e03", "s01e04"}
    assert "s01e05" not in triage  # human-reviewed — never graded


def test_grade_all_writes_grade_and_critique_per_record(episodes_dir: Path) -> None:
    client = StubClient(["A: ship it", "C: wrong monster"])
    out = episodes_dir.parent / "logline_triage.json"

    grade_all(client, episodes_dir, out)

    triage = load_triage(out)
    assert triage["s01e03"]["grade"] == "A"
    assert triage["s01e04"]["grade"] == "C"
    assert triage["s01e04"]["critique"] == "wrong monster"


def test_grade_all_never_writes_the_episode_records(episodes_dir: Path) -> None:
    """Triage is read-only over the records — the sacred layer is untouched."""
    before = {p.name: p.read_text() for p in episodes_dir.glob("*.json")}
    client = StubClient(["A: good", "B: fine"])

    grade_all(client, episodes_dir, episodes_dir.parent / "logline_triage.json")

    after = {p.name: p.read_text() for p in episodes_dir.glob("*.json")}
    assert after == before


def test_grade_all_merges_into_an_existing_triage_file(episodes_dir: Path) -> None:
    """Re-running after fixing a few drafts updates in place, never resets."""
    out = episodes_dir.parent / "logline_triage.json"
    out.write_text(json.dumps({"s01e03": {"grade": "C", "critique": "old"}}))

    client = StubClient(["A: now good", "B: fine"])
    grade_all(client, episodes_dir, out)

    triage = load_triage(out)
    assert triage["s01e03"]["grade"] == "A"  # overwritten with the fresh grade
    assert triage["s01e04"]["grade"] == "B"


def test_load_triage_of_a_missing_file_is_empty() -> None:
    assert load_triage(Path("/nonexistent/triage.json")) == {}


class NoTextClient:
    """A client that never returns a text block for a chosen title —
    the real failure that killed the first full run (the model thinks but
    emits no text). Everything else grades A."""

    def __init__(self, fail_title: str) -> None:
        self._fail_title = fail_title
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        content = kwargs["messages"][0]["content"]
        if self._fail_title in content:
            return SimpleNamespace(content=[])  # no text block, ever
        return SimpleNamespace(content=[SimpleNamespace(text="A: good")])


def test_a_single_ungradeable_record_does_not_discard_the_batch(
    episodes_dir: Path,
) -> None:
    """The first full run lost 214 grades when record 215 failed. Progress
    must be persisted incrementally so one bad record can't wipe the rest."""
    out = episodes_dir.parent / "logline_triage.json"
    # s01e04 is titled "Conduit"; make only that record ungradeable.
    client = NoTextClient(fail_title="Conduit")

    grade_all(client, episodes_dir, out)  # must NOT raise

    triage = load_triage(out)
    assert triage["s01e03"]["grade"] == "A"  # the good grade survived
    assert "s01e04" not in triage  # the failed record simply has no grade


def test_grade_all_writes_after_each_record(episodes_dir: Path) -> None:
    """Persisted incrementally, not only at the end — so a crash mid-batch
    keeps every grade already earned."""
    out = episodes_dir.parent / "logline_triage.json"
    seen: list[int] = []

    class CountingClient:
        def __init__(self) -> None:
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **_kwargs):
            # Record how many grades are already on disk before this call
            # resolves — proves earlier grades were flushed, not buffered.
            seen.append(len(load_triage(out)))
            return SimpleNamespace(content=[SimpleNamespace(text="A: good")])

    grade_all(CountingClient(), episodes_dir, out)

    # Second record's call sees the first already written to disk.
    assert seen == [0, 1]
