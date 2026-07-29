from __future__ import annotations

from pathlib import Path

import pandas as pd
from dash import dash_table

from components.table import build_episode_table
from spooky.loader import load_episodes

EPISODES_DIR = Path(__file__).resolve().parent.parent / "data" / "episodes"


def test_build_episode_table_returns_expected_columns(
    episodes_df: pd.DataFrame,
) -> None:
    table = build_episode_table(episodes_df)
    props = table.to_plotly_json()["props"]

    assert isinstance(table, dash_table.DataTable)
    assert [column["name"] for column in props["columns"]] == [
        "Season/Ep",
        "Title",
        "Type",
        "Air date",
        "Category",
        "TVmaze rating",
        "Contested",
    ]


def test_table_is_sortable_but_has_no_white_box_controls(
    episodes_df: pd.DataFrame,
) -> None:
    """Per-column filter inputs and native pagination are the stock light-
    theme controls — deliberately off. Season paging and the search input
    outside the table drive the view instead."""
    table = build_episode_table(episodes_df)
    props = table.to_plotly_json()["props"]

    assert props["sort_action"] == "native"
    assert props["filter_action"] == "none"
    assert props["page_action"] == "none"


def test_table_shows_every_row_it_is_given(episodes_df: pd.DataFrame) -> None:
    props = build_episode_table(episodes_df).to_plotly_json()["props"]

    assert len(props["data"]) == len(episodes_df)


def test_type_column_distinguishes_films_from_episodes() -> None:
    df = load_episodes(EPISODES_DIR)

    props = build_episode_table(df).to_plotly_json()["props"]
    types = {row["record_type"] for row in props["data"]}
    films = [row for row in props["data"] if row["record_type"] == "Film"]

    assert types == {"Episode", "Film"}
    assert len(films) == 2
    assert {row["season_episode"] for row in films} == {"Film"}


def test_contested_rows_carry_the_badge(episodes_df: pd.DataFrame) -> None:
    props = build_episode_table(episodes_df).to_plotly_json()["props"]

    contested_rows = [row for row in props["data"] if row["contested_badge"]]
    assert len(contested_rows) >= 1
    assert contested_rows[0]["contested_badge"] == "Contested"


def test_table_carries_explicit_dark_theme_styles(
    episodes_df: pd.DataFrame,
) -> None:
    """The DataTable does not inherit page CSS — without explicit style
    props it renders its default light theme on the dark page, near-invisible.
    """
    props = build_episode_table(episodes_df).to_plotly_json()["props"]

    for style_key in ("style_header", "style_cell"):
        style = props.get(style_key)
        assert style, f"{style_key} not set — table falls back to light theme"
        assert "backgroundColor" in style and "color" in style
