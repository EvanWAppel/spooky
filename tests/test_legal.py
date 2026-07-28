"""The legal-shape tests (TASKS B-13, E-10; CLAUDE.md hard prohibitions).

These run against the committed dataset in ``data/episodes/`` — the source
of truth the site and the published artifacts are built from. C1: no IMDb
ratings. C2: no imagery, no static.tvmaze.com. C3: no synopses; loglines
capped at 30 words.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

EPISODES_DIR = Path(__file__).resolve().parent.parent / "data" / "episodes"

FORBIDDEN_KEYS = {"synopsis", "summary", "image", "images", "screencap"}
LOGLINE_WORD_CAP = 30


def _records() -> list[dict]:
    files = sorted(EPISODES_DIR.glob("*.json"))
    if not files:
        pytest.skip("data/episodes/ is empty — run the merge first")
    return [json.loads(f.read_text()) for f in files]


def test_no_record_carries_a_forbidden_key() -> None:
    for record in _records():
        present = FORBIDDEN_KEYS & set(record)
        assert not present, f"{record['id']}: forbidden keys {present}"


def test_no_imdb_rating_field_anywhere() -> None:
    """C1: TVmaze ratings only. An IMDb-sourced number must never ship."""
    for record in _records():
        assert "imdb_rating" not in record
        rating_provenance = record.get("provenance", {}).get("rating")
        if rating_provenance:
            assert "IMDb" not in rating_provenance["source"]


def test_no_tvmaze_image_urls_leak_into_records() -> None:
    """C2: no hotlinking static.tvmaze.com."""
    for record in _records():
        blob = json.dumps(record)
        assert "static.tvmaze.com" not in blob, record["id"]


def test_loglines_respect_the_30_word_cap() -> None:
    for record in _records():
        for field in ("logline", "logline_generated"):
            value = record.get(field)
            if value:
                words = len(value.split())
                assert words <= LOGLINE_WORD_CAP, f"{record['id']}.{field}: {words} words"


def test_every_record_has_the_full_label_set() -> None:
    for record in _records():
        assert record["label_derived"] in {
            "mythology",
            "monster-of-the-week",
            "standalone",
        }
        assert isinstance(record["label_contested"], bool)
        assert record["label_rationale"]
