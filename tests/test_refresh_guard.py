"""Tests for the refresh diff guard (TASKS I-05).

The scheduled refresh must fail loudly rather than silently republishing
over the owner's reviewed prose. This tests the check the workflow runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.check_refresh_diff import violations


def _record(**overrides) -> dict:
    base = {
        "id": "s01e03",
        "title": "Squeeze",
        "logline": "Evan's approved logline.",
        "logline_generated": "a machine draft",
        "review_status": "human-reviewed",
        "reviewed_at": "2026-07-27T00:00:00Z",
        "review_note": None,
    }
    return {**base, **overrides}


@pytest.fixture
def committed(monkeypatch: pytest.MonkeyPatch):
    """Stub the committed version git would return for a path."""

    def _install(version: dict | None):
        monkeypatch.setattr(
            "tools.check_refresh_diff.committed_version", lambda _path: version
        )

    return _install


def _write(tmp_path: Path, record: dict) -> str:
    path = tmp_path / f"{record['id']}.json"
    path.write_text(json.dumps(record))
    return str(path)


def test_machine_only_changes_are_clean(tmp_path: Path, committed) -> None:
    committed(_record())
    path = _write(tmp_path, _record(logline_generated="a NEWER machine draft"))

    assert violations([path]) == []


def test_changed_logline_on_a_reviewed_record_is_a_violation(
    tmp_path: Path, committed
) -> None:
    committed(_record())
    path = _write(tmp_path, _record(logline="something the machine wrote instead"))

    found = violations([path])

    assert len(found) == 1
    assert "logline" in found[0]
    # The message shows both sides so the failure is diagnosable from CI logs.
    assert "Evan's approved logline." in found[0]
    assert "something the machine wrote instead" in found[0]


def test_downgraded_review_status_is_a_violation(tmp_path: Path, committed) -> None:
    committed(_record())
    path = _write(tmp_path, _record(review_status="unreviewed", reviewed_at=None))

    found = violations([path])

    assert any("review_status" in v for v in found)
    assert any("reviewed_at" in v for v in found)


def test_unreviewed_records_are_free_to_change(tmp_path: Path, committed) -> None:
    """Only the reviewed layer is sacred — machine records refresh freely."""
    committed(_record(review_status="ai-drafted", logline=None))
    path = _write(
        tmp_path, _record(review_status="ai-drafted", logline="anything at all")
    )

    assert violations([path]) == []


def test_newly_added_records_are_not_violations(tmp_path: Path, committed) -> None:
    committed(None)  # git show fails for a file that isn't committed yet
    path = _write(tmp_path, _record())

    assert violations([path]) == []
