"""The sacred-edits test (TASKS B-12, E-05; CLAUDE.md data rules).

Human-reviewed content is sacred: no pipeline step — merge or scheduled
refresh — may overwrite a human-owned field on a record whose
``review_status`` is ``human-reviewed``. The guard raises with a diff; it
never skips silently.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from build.merge import ReviewGuardError, write_record


def _record(**overrides) -> dict:
    base = {
        "id": "s01e03",
        "title": "Squeeze",
        "logline_generated": "machine draft",
        "logline": "machine draft",
        "review_status": "unreviewed",
        "reviewed_at": None,
        "review_note": None,
    }
    return {**base, **overrides}


def test_fresh_record_writes_cleanly(tmp_path: Path) -> None:
    out = write_record(tmp_path, _record())

    assert json.loads(out.read_text())["id"] == "s01e03"


def test_machine_refresh_preserves_human_reviewed_fields(tmp_path: Path) -> None:
    """A refresh carrying only machine changes keeps the human layer intact."""
    write_record(
        tmp_path,
        _record(
            logline="Evan's hand-polished logline.",
            review_status="human-reviewed",
            reviewed_at="2026-07-27T00:00:00Z",
        ),
    )

    refreshed = write_record(tmp_path, _record(logline_generated="new machine draft"))

    written = json.loads(refreshed.read_text())
    assert written["logline"] == "Evan's hand-polished logline."
    assert written["review_status"] == "human-reviewed"
    assert written["logline_generated"] == "new machine draft"


def test_overwriting_a_reviewed_logline_raises_with_diff(tmp_path: Path) -> None:
    write_record(
        tmp_path,
        _record(
            logline="Evan's hand-polished logline.",
            review_status="human-reviewed",
            reviewed_at="2026-07-27T00:00:00Z",
        ),
    )

    hostile = _record(
        logline="a different logline the machine wants to force",
        review_status="human-reviewed",
        reviewed_at="2026-07-27T00:00:00Z",
    )
    with pytest.raises(ReviewGuardError, match="logline"):
        write_record(tmp_path, hostile)

    # And the file on disk is unchanged.
    kept = json.loads((tmp_path / "s01e03.json").read_text())
    assert kept["logline"] == "Evan's hand-polished logline."


def test_regen_changes_zero_human_reviewed_records(tmp_path: Path) -> None:
    """F-06: re-running logline generation after review is a no-op for every
    reviewed record — no API call, no write."""
    from build.loglines import generate_all

    episodes = tmp_path / "episodes"
    episodes.mkdir()
    reviewed = _record(
        logline="Evan's approved logline.",
        logline_generated="an old draft",
        review_status="human-reviewed",
        reviewed_at="2026-07-27T00:00:00Z",
    )
    (episodes / "s01e03.json").write_text(json.dumps(reviewed))

    class ExplodingClient:
        def __getattr__(self, name):
            raise AssertionError("regeneration touched the API for a reviewed record")

    written = generate_all(ExplodingClient(), episodes, sections={})

    assert written == 0
    assert json.loads((episodes / "s01e03.json").read_text()) == reviewed


def test_refresh_preserves_every_human_reviewed_field(tmp_path: Path) -> None:
    """I-05: the scheduled refresh re-runs the merge over the real records.

    Simulates that at the write layer the refresh actually uses: a fresh
    machine record for an already-reviewed episode must leave the whole
    human layer untouched while machine fields still update.
    """
    episodes = tmp_path / "episodes"
    reviewed = _record(
        logline="Evan's approved logline.",
        review_status="human-reviewed",
        reviewed_at="2026-07-27T00:00:00Z",
        review_note="checked against the DVD",
    )
    write_record(episodes, reviewed)

    # What a refresh produces: machine fields fresh, human layer blank.
    refreshed = _record(
        title="Squeeze",
        logline_generated="a newly drafted logline",
        logline=None,
        review_status="unreviewed",
        reviewed_at=None,
        review_note=None,
    )
    write_record(episodes, refreshed)

    written = json.loads((episodes / "s01e03.json").read_text())
    for field, expected in (
        ("logline", "Evan's approved logline."),
        ("review_status", "human-reviewed"),
        ("reviewed_at", "2026-07-27T00:00:00Z"),
        ("review_note", "checked against the DVD"),
    ):
        assert written[field] == expected, f"refresh clobbered {field}"
    assert written["logline_generated"] == "a newly drafted logline"


def test_guard_error_message_shows_both_versions(tmp_path: Path) -> None:
    write_record(
        tmp_path,
        _record(logline="the original", review_status="human-reviewed"),
    )

    with pytest.raises(ReviewGuardError) as excinfo:
        write_record(
            tmp_path,
            _record(logline="the replacement", review_status="human-reviewed"),
        )

    message = str(excinfo.value)
    assert "the original" in message
    assert "the replacement" in message
