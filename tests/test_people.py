"""Tests for crew credit extraction (TASKS D-12).

PRD §8.1 landmine: TVmaze credits writers under three guestCrewTypes —
``Writer``, ``Story``, and ``Teleplay``. Filtering on ``Writer`` alone
silently drops 11 episodes (the story/teleplay-split ones). The fixture is
distilled from the real 436-call sweep of 2026-07-27.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from build.people import extract_directors, extract_writers

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "guestcrew_types.json"


@pytest.fixture(scope="module")
def crew_by_episode() -> dict[str, list[dict]]:
    return json.loads(FIXTURE.read_text())


def test_writer_union_covers_every_episode(crew_by_episode) -> None:
    missing = [
        episode_id
        for episode_id, members in crew_by_episode.items()
        if not extract_writers(members)
    ]

    assert missing == []


def test_writer_only_filtering_would_drop_11_episodes(crew_by_episode) -> None:
    """Documents the landmine the union exists to avoid."""
    writer_only = [
        episode_id
        for episode_id, members in crew_by_episode.items()
        if any(m["guestCrewType"] == "Writer" for m in members)
    ]
    with_union = [
        episode_id
        for episode_id, members in crew_by_episode.items()
        if extract_writers(members)
    ]

    assert len(with_union) - len(writer_only) == 11


def test_every_episode_has_a_director(crew_by_episode) -> None:
    missing = [
        episode_id
        for episode_id, members in crew_by_episode.items()
        if not extract_directors(members)
    ]

    assert missing == []


def test_extract_writers_unions_and_dedupes_in_order() -> None:
    members = [
        {"guestCrewType": "Story", "name": "Anne Simon"},
        {"guestCrewType": "Teleplay", "name": "Chris Carter"},
        {"guestCrewType": "Story", "name": "Chris Carter"},
        {"guestCrewType": "Director", "name": "Kim Manners"},
    ]

    assert extract_writers(members) == ["Anne Simon", "Chris Carter"]
    assert extract_directors(members) == ["Kim Manners"]
