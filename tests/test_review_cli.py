"""Tests for the logline review CLI (TASKS F-03, F-04, F-05).

The CLI is the only path by which machine-drafted prose becomes
human-owned. Approve copies the draft into `logline`; edit stores the
owner's own words; reject sends it back with a note. All three write
`data/episodes/*.json` in place.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.review import (
    ReviewError,
    approve,
    edit,
    load_records,
    order_queue,
    pending,
    reject,
    reset,
    run_interactive,
    status_line,
)


def _record(**overrides) -> dict:
    base = {
        "id": "s01e03",
        "title": "Squeeze",
        "season": 1,
        "episode": 3,
        "air_date": "1993-09-24",
        "label_derived": "monster-of-the-week",
        "label_contested": False,
        "director": ["Harry Longstreet"],
        "writers": ["Glen Morgan", "James Wong"],
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
                reviewed_at="2026-07-27T00:00:00Z",
            )
        )
    )
    return directory


def test_pending_skips_human_reviewed_records(episodes_dir: Path) -> None:
    ids = [record["id"] for record in pending(load_records(episodes_dir))]

    assert ids == ["s01e03", "s01e04"]


def test_approve_copies_the_draft_and_promotes(episodes_dir: Path) -> None:
    approve(episodes_dir, "s01e03", now="2026-07-28T12:00:00Z")

    written = json.loads((episodes_dir / "s01e03.json").read_text())
    assert written["logline"] == "A killer who squeezes through impossible gaps."
    assert written["review_status"] == "human-reviewed"
    assert written["reviewed_at"] == "2026-07-28T12:00:00Z"
    # The draft is preserved so the two layers stay distinguishable.
    assert written["logline_generated"] == (
        "A killer who squeezes through impossible gaps."
    )


def test_edit_stores_the_owners_text(episodes_dir: Path) -> None:
    edit(episodes_dir, "s01e03", "Eugene Tooms hunts livers through the ductwork.")

    written = json.loads((episodes_dir / "s01e03.json").read_text())
    assert written["logline"] == "Eugene Tooms hunts livers through the ductwork."
    assert written["review_status"] == "human-reviewed"
    assert written["logline_generated"] != written["logline"]


def test_edit_enforces_the_word_cap(episodes_dir: Path) -> None:
    """C3 is a legal constraint — it binds the owner's own text too."""
    with pytest.raises(ReviewError, match="30 words"):
        edit(episodes_dir, "s01e03", " ".join(["word"] * 31))

    unchanged = json.loads((episodes_dir / "s01e03.json").read_text())
    assert unchanged["logline"] is None


def test_edit_rejects_empty_text(episodes_dir: Path) -> None:
    with pytest.raises(ReviewError, match="empty"):
        edit(episodes_dir, "s01e03", "   ")


def test_reject_marks_needs_work_with_the_note(episodes_dir: Path) -> None:
    reject(episodes_dir, "s01e03", "Wrong monster — this is the liver-eater.")

    written = json.loads((episodes_dir / "s01e03.json").read_text())
    assert written["review_status"] == "needs-work"
    assert written["review_note"] == "Wrong monster — this is the liver-eater."
    assert written["logline"] is None


def test_rejected_records_stay_pending(episodes_dir: Path) -> None:
    reject(episodes_dir, "s01e03", "needs another pass")

    ids = [record["id"] for record in pending(load_records(episodes_dir))]
    assert "s01e03" in ids


def test_status_line_counts_reviewed_over_total(episodes_dir: Path) -> None:
    assert status_line(load_records(episodes_dir)) == "1 / 3 human-reviewed"

    approve(episodes_dir, "s01e03", now="2026-07-28T12:00:00Z")
    assert status_line(load_records(episodes_dir)) == "2 / 3 human-reviewed"


def test_approve_refuses_a_record_with_no_draft(episodes_dir: Path) -> None:
    (episodes_dir / "s01e06.json").write_text(
        json.dumps(
            _record(id="s01e06", logline_generated=None, review_status="unreviewed")
        )
    )

    with pytest.raises(ReviewError, match="no draft"):
        approve(episodes_dir, "s01e06", now="2026-07-28T12:00:00Z")


def test_unknown_id_raises(episodes_dir: Path) -> None:
    with pytest.raises(ReviewError, match="s99e99"):
        approve(episodes_dir, "s99e99", now="2026-07-28T12:00:00Z")


def _answers(*replies: str):
    """An `ask` callable that returns each reply in turn."""
    queue = list(replies)

    def _ask(_prompt: str) -> str:
        if not queue:
            raise AssertionError("the CLI asked for more input than expected")
        return queue.pop(0)

    return _ask


def test_ctrl_c_exits_cleanly_without_a_traceback(episodes_dir: Path, capsys) -> None:
    """A 220-record queue will not be finished in one sitting — quitting
    mid-review must not look like a crash."""

    def _interrupt(_prompt: str) -> str:
        raise KeyboardInterrupt

    run_interactive(episodes_dir, ask=_interrupt)  # must not raise

    assert "human-reviewed" in capsys.readouterr().out


def test_ctrl_d_exits_cleanly(episodes_dir: Path, capsys) -> None:
    def _eof(_prompt: str) -> str:
        raise EOFError

    run_interactive(episodes_dir, ask=_eof)

    assert "human-reviewed" in capsys.readouterr().out


def test_interrupting_keeps_everything_already_decided(
    episodes_dir: Path,
) -> None:
    """Each verdict is written immediately, so quitting loses nothing."""
    replies = iter(["a"])

    def _ask(_prompt: str) -> str:
        try:
            return next(replies)
        except StopIteration:
            raise KeyboardInterrupt from None

    run_interactive(episodes_dir, ask=_ask)

    first = json.loads((episodes_dir / "s01e03.json").read_text())
    assert first["review_status"] == "human-reviewed"


def test_bare_enter_never_approves(episodes_dir: Path) -> None:
    """Enter used to mean approve — a stray keypress after a typo silently
    committed a review. It must re-prompt instead."""
    run_interactive(episodes_dir, ask=_answers("", "  ", "q"))

    untouched = json.loads((episodes_dir / "s01e03.json").read_text())
    assert untouched["review_status"] == "ai-drafted"
    assert untouched["logline"] is None


def test_unrecognized_input_never_approves(episodes_dir: Path) -> None:
    run_interactive(episodes_dir, ask=_answers("Cool season, bruh", "q"))

    untouched = json.loads((episodes_dir / "s01e03.json").read_text())
    assert untouched["review_status"] == "ai-drafted"


def test_quit_stops_before_the_next_record(episodes_dir: Path) -> None:
    run_interactive(episodes_dir, ask=_answers("a", "q"))

    assert (
        json.loads((episodes_dir / "s01e03.json").read_text())["review_status"]
        == "human-reviewed"
    )
    assert (
        json.loads((episodes_dir / "s01e04.json").read_text())["review_status"]
        == "ai-drafted"
    )


def test_order_queue_puts_worst_grade_first(episodes_dir: Path) -> None:
    """With triage in hand, review C's first while attention is freshest;
    the fast A's batch at the end."""
    queue = pending(load_records(episodes_dir))
    # s01e03 graded A, s01e04 graded C — C must come first.
    triage = {
        "s01e03": {"grade": "A", "critique": "ship it"},
        "s01e04": {"grade": "C", "critique": "rewrite"},
    }

    ordered = [r["id"] for r in order_queue(queue, triage)]

    assert ordered == ["s01e04", "s01e03"]


def test_order_queue_keeps_air_order_within_a_grade(episodes_dir: Path) -> None:
    queue = pending(load_records(episodes_dir))
    triage = {
        "s01e03": {"grade": "B", "critique": "x"},
        "s01e04": {"grade": "B", "critique": "y"},
    }

    ordered = [r["id"] for r in order_queue(queue, triage)]

    assert ordered == ["s01e03", "s01e04"]


def test_order_queue_puts_ungraded_records_last(episodes_dir: Path) -> None:
    queue = pending(load_records(episodes_dir))
    triage = {"s01e04": {"grade": "A", "critique": "ship it"}}  # s01e03 ungraded

    ordered = [r["id"] for r in order_queue(queue, triage)]

    assert ordered == ["s01e04", "s01e03"]


def test_order_queue_without_triage_keeps_air_order(episodes_dir: Path) -> None:
    queue = pending(load_records(episodes_dir))

    ordered = [r["id"] for r in order_queue(queue, {})]

    assert ordered == ["s01e03", "s01e04"]


def test_review_renders_the_critique_text(episodes_dir: Path, capsys) -> None:
    triage = {"s01e04": {"grade": "C", "critique": "invents a plot detail"}}
    run_interactive(episodes_dir, ask=_answers("s", "s", "q"), triage=triage)

    out = capsys.readouterr().out
    assert "invents a plot detail" in out


def test_reset_returns_a_record_to_the_queue(episodes_dir: Path) -> None:
    """The escape hatch for an approval you did not mean to make."""
    approve(episodes_dir, "s01e03", now="2026-07-28T12:00:00Z")

    reset(episodes_dir, "s01e03")

    record = json.loads((episodes_dir / "s01e03.json").read_text())
    assert record["review_status"] == "ai-drafted"
    assert record["logline"] is None
    assert record["reviewed_at"] is None
    # The machine draft survives, so it can be reviewed again.
    assert record["logline_generated"]
    assert "s01e03" in [r["id"] for r in pending(load_records(episodes_dir))]
