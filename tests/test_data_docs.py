"""The field dictionary must match the published data (TASKS E-09, J-07).

A dataset is only as useful as its documentation is accurate, so the docs
are checked against the data programmatically rather than by eye.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST = REPO_ROOT / "data" / "dist" / "spooky-episodes.json"
DATA_README = REPO_ROOT / "data" / "README.md"


def _records() -> list[dict]:
    if not DIST.exists():
        pytest.skip("data/dist is empty — run `python -m build --only emit`")
    return json.loads(DIST.read_text())


def _documented_fields() -> set[str]:
    """Field names from the field-dictionary table only.

    Scoped to that section so other tables — the review-state table uses
    the same leading-backtick column shape — cannot masquerade as fields.
    """
    text = DATA_README.read_text()
    start = text.index("## Field dictionary")
    end = text.index("### Review states", start)
    return set(re.findall(r"^\| `(\w+)`", text[start:end], re.M))


def test_every_published_field_is_documented() -> None:
    fields = {key for record in _records() for key in record}

    assert fields - _documented_fields() == set()


def test_no_documented_field_is_missing_from_the_data() -> None:
    fields = {key for record in _records() for key in record}

    assert _documented_fields() - fields == set()


def test_every_review_state_in_the_data_is_documented() -> None:
    """The states grew during Group F — the docs must keep up."""
    states = {record["review_status"] for record in _records()}
    documented = DATA_README.read_text()

    for state in states:
        assert f"`{state}`" in documented, f"review state {state!r} undocumented"


def test_only_reviewed_records_carry_a_logline() -> None:
    """The invariant the docs promise: `logline` is the human layer."""
    for record in _records():
        if record["review_status"] != "human-reviewed":
            assert record["logline"] is None, (
                f"{record['id']}: unreviewed record has a logline"
            )
