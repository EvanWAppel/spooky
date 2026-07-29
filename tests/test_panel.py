from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
import pytest

from components.panel import build_detail_panel


def test_build_detail_panel_renders_episode_details_links_and_status(
    contested_record: dict[str, Any],
    render_text: Callable[[Any], str],
) -> None:
    panel = build_detail_panel(contested_record)
    rendered = render_text(panel)

    assert contested_record["title"] in rendered
    assert contested_record["logline"] in rendered
    assert "Chris Carter" in rendered
    assert "Monster-of-the-Week" in rendered
    assert "Human-reviewed" in rendered
    assert "Fox DVDs:" in rendered
    assert "Wikipedia:" in rendered
    assert "dom111:" in rendered
    assert "https://www.imdb.com/title/" in rendered
    assert "https://www.themoviedb.org/tv/4087-the-x-files/watch" in rendered


def test_source_breakdown_never_renders_raw_nan(
    episodes_df: pd.DataFrame,
    render_text: Callable[[Any], str],
) -> None:
    """A source that does not cover a record must not surface as "nan".

    JSON `null` becomes `float('nan')` through pandas, so `is None` guards do
    not catch it and f-strings render the literal string "nan". The Fox
    "Mythology" DVD sets predate the revival, so every season 10-11 record has
    a null `label_fox_dvd` — this is the common case, not an edge case.
    """
    record = episodes_df[episodes_df["id"] == "s10e01"].iloc[0].to_dict()
    assert pd.isna(record["label_fox_dvd"]), "fixture must have a null Fox label"

    rendered = render_text(build_detail_panel(record))

    assert "nan" not in rendered.lower().split()
    assert "Fox DVDs: no data" in rendered


def test_source_breakdown_distinguishes_no_data_from_not_listed(
    episodes_df: pd.DataFrame,
    render_text: Callable[[Any], str],
) -> None:
    """ "Not listed" is evidence; a null is the absence of evidence."""
    record = episodes_df[episodes_df["id"] == "s10e01"].iloc[0].to_dict()
    record["label_fox_dvd"] = "not-listed"

    rendered = render_text(build_detail_panel(record))

    assert "Fox DVDs: not listed" in rendered


def test_null_logline_never_renders_as_the_string_none(
    episodes_df: pd.DataFrame,
    render_text: Callable[[Any], str],
) -> None:
    """A record with neither logline nor draft omits the paragraph — it
    never prints "None"."""
    record = episodes_df.iloc[0].to_dict()
    record["logline"] = None
    record["logline_generated"] = None
    record["review_status"] = "unreviewed"

    rendered = render_text(build_detail_panel(record))

    assert "None" not in rendered.split()


def test_ai_draft_shows_with_its_badge(
    episodes_df: pd.DataFrame,
    render_text: Callable[[Any], str],
) -> None:
    """F-08: an unreviewed record shows the machine draft, clearly badged."""
    record = episodes_df.iloc[0].to_dict()
    record["logline"] = None
    record["logline_generated"] = "A machine-drafted teaser for this episode."
    record["review_status"] = "ai-drafted"

    rendered = render_text(build_detail_panel(record))

    assert "A machine-drafted teaser for this episode." in rendered
    assert "AI-drafted" in rendered


def test_reviewed_logline_wins_over_the_draft_and_carries_its_badge(
    episodes_df: pd.DataFrame,
    render_text: Callable[[Any], str],
) -> None:
    """F-08: once reviewed, the human text shows with the reviewed badge."""
    record = episodes_df.iloc[0].to_dict()
    record["logline"] = "Evan's approved description."
    record["logline_generated"] = "the superseded machine draft"
    record["review_status"] = "human-reviewed"

    rendered = render_text(build_detail_panel(record))

    assert "Evan's approved description." in rendered
    assert "Human-reviewed" in rendered
    assert "the superseded machine draft" not in rendered


@pytest.mark.parametrize("missing", [None, float("nan"), pd.NA])
def test_film_record_renders_without_crashing(
    episodes_df: pd.DataFrame,
    render_text: Callable[[Any], str],
    missing: Any,
) -> None:
    """Films are first-class records with no season or episode (PRD §3.1).

    pandas represents those as NaN/NA rather than None, so a bare `is None`
    check falls through to `int(nan)` and raises.
    """
    record = episodes_df.iloc[0].to_dict()
    record["title"] = "The X-Files: Fight the Future"
    record["season"] = missing
    record["episode"] = missing

    rendered = render_text(build_detail_panel(record))

    assert "Film" in rendered
    assert "The X-Files: Fight the Future" in rendered
