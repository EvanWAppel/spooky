"""Provenance / pipeline dashboard data shaping (Group R.2, TASKS R-05).

TDD: written before ``spooky/provenance.py`` and ``components/provenance_view.py``
exist. Everything is **re-derived** from the loaded records — no count is ever
hard-coded (CLAUDE.md: "Do not hard-code '218' or '71'").
"""

from __future__ import annotations

import pandas as pd
import pytest

from spooky.provenance import (
    SOURCES,
    contested_breakdown,
    field_provenance,
    source_coverage,
)


def _df(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame.from_records(records)


@pytest.fixture
def labelled():
    # Two Fox-covered records, one revival (Fox abstains), one film (dom111
    # abstains); a mix of mythology verdicts and one contested row.
    return _df(
        [
            {
                "id": "s01e01",
                "title": "Pilot",
                "season_episode": "S01E01",
                "label_fox_dvd": "mythology",
                "label_wikipedia": "mythology",
                "label_dom111": "mythology",
                "label_derived": "mythology",
                "label_contested": False,
                "label_rationale": "3 of 3 sources say mythology.",
                "provenance": {
                    "title": {
                        "source": "Wikipedia",
                        "license": "CC BY-SA 4.0",
                        "revid": 1,
                    },
                    "rating": {"source": "TVmaze", "license": "CC BY-SA 4.0"},
                },
            },
            {
                "id": "s01e02",
                "title": "Squeeze",
                "season_episode": "S01E02",
                "label_fox_dvd": "not-listed",
                "label_wikipedia": "not-flagged",
                "label_dom111": "motw",
                "label_derived": "monster-of-the-week",
                "label_contested": False,
                "label_rationale": "0 of 3 sources say mythology.",
                "provenance": {
                    "title": {
                        "source": "Wikipedia",
                        "license": "CC BY-SA 4.0",
                        "revid": 2,
                    },
                    "tvmaze_id": {"source": "TVmaze", "license": "CC BY-SA 4.0"},
                },
            },
            {
                "id": "s10e01",
                "title": "My Struggle",
                "season_episode": "S10E01",
                "label_fox_dvd": None,  # Fox DVDs predate the revival: abstains
                "label_wikipedia": "mythology",
                "label_dom111": "motw",
                "label_derived": "mythology",
                "label_contested": True,
                "label_rationale": "Sources disagree; fewer than 3 cover it.",
                "provenance": {
                    "title": {
                        "source": "Wikipedia",
                        "license": "CC BY-SA 4.0",
                        "revid": 3,
                    },
                },
            },
            {
                "id": "ftf",
                "title": "Fight the Future",
                "season_episode": "Film",
                "label_fox_dvd": "mythology",
                "label_wikipedia": "mythology",
                "label_dom111": None,  # dom111 covers only the 218 TV episodes
                "label_derived": "mythology",
                "label_contested": True,
                "label_rationale": "Only 2 sources cover it.",
                "provenance": {
                    "tmdb_movie_id": {"source": "Wikidata", "license": "CC0"},
                },
            },
        ]
    )


def test_sources_are_the_three_label_columns():
    assert {s.column for s in SOURCES} == {
        "label_fox_dvd",
        "label_wikipedia",
        "label_dom111",
    }


def test_source_coverage_counts_coverage_abstention_and_mythology(labelled):
    by_col = {row["column"]: row for row in source_coverage(labelled)}

    fox = by_col["label_fox_dvd"]
    assert fox["covers"] == 3 and fox["abstains"] == 1  # revival record abstains
    assert fox["mythology"] == 2

    dom = by_col["label_dom111"]
    assert dom["covers"] == 3 and dom["abstains"] == 1  # the film abstains
    assert dom["mythology"] == 1

    wiki = by_col["label_wikipedia"]
    assert wiki["covers"] == 4 and wiki["abstains"] == 0
    assert wiki["mythology"] == 3


def test_source_coverage_is_rederived_not_hardcoded(labelled):
    subset = labelled.iloc[:2]
    fox = {r["column"]: r for r in source_coverage(subset)}["label_fox_dvd"]
    assert fox["covers"] == 2 and fox["mythology"] == 1  # tracks the smaller frame


def test_contested_breakdown_lists_only_contested_with_per_source_split(labelled):
    rows = contested_breakdown(labelled)
    assert {r["id"] for r in rows} == {"s10e01", "ftf"}
    revival = next(r for r in rows if r["id"] == "s10e01")
    assert revival["label_fox_dvd"] is None
    assert revival["label_wikipedia"] == "mythology"
    assert revival["label_dom111"] == "motw"
    assert revival["label_derived"] == "mythology"
    assert "disagree" in revival["label_rationale"].lower()


def test_field_provenance_aggregates_sources_licenses_and_revid(labelled):
    by_field = {row["field"]: row for row in field_provenance(labelled)}

    assert by_field["title"]["sources"] == ["Wikipedia"]
    assert by_field["title"]["licenses"] == ["CC BY-SA 4.0"]
    assert by_field["title"]["has_revid"] is True

    assert by_field["rating"]["sources"] == ["TVmaze"]
    assert by_field["rating"]["has_revid"] is False

    assert by_field["tmdb_movie_id"]["sources"] == ["Wikidata"]
    assert by_field["tmdb_movie_id"]["licenses"] == ["CC0"]


def test_field_provenance_is_sorted_and_deduped(labelled):
    fields = [row["field"] for row in field_provenance(labelled)]
    assert fields == sorted(fields)
    assert len(fields) == len(set(fields))


# --- the rendered Dash view ---


def test_view_shows_the_rederived_contested_count(episodes_df, render_text):
    from components.provenance_view import build_provenance_view

    text = render_text(build_provenance_view(episodes_df))
    contested = int(episodes_df["label_contested"].sum())
    assert str(contested) in text
    # Every source is named on the page.
    for source in SOURCES:
        assert source.label in text
