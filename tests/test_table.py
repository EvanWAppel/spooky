from __future__ import annotations

import pandas as pd
from dash import dash_table

from components.table import build_episode_table


def test_build_episode_table_returns_expected_columns(
    episodes_df: pd.DataFrame,
) -> None:
    table = build_episode_table(episodes_df)
    props = table.to_plotly_json()["props"]

    assert isinstance(table, dash_table.DataTable)
    assert [column["name"] for column in props["columns"]] == [
        "Season/Ep",
        "Title",
        "Air date",
        "Category",
        "TVmaze rating",
        "Contested",
    ]


def test_build_episode_table_is_sortable_filterable_and_marks_contested(
    episodes_df: pd.DataFrame,
) -> None:
    table = build_episode_table(episodes_df)
    props = table.to_plotly_json()["props"]

    assert props["sort_action"] == "native"
    assert props["filter_action"] == "native"
    contested_rows = [row for row in props["data"] if row["contested_badge"]]
    assert len(contested_rows) >= 1
    assert contested_rows[0]["contested_badge"] == "Contested"


def test_table_carries_explicit_dark_theme_styles(
    episodes_df: pd.DataFrame,
) -> None:
    """The DataTable does not inherit page CSS — without explicit style
    props it renders its default light theme on the dark page, near-invisible.
    Every styled surface (header, cells, filter row) must set both a dark
    background and a light foreground.
    """
    props = build_episode_table(episodes_df).to_plotly_json()["props"]

    for style_key in ("style_header", "style_cell", "style_filter"):
        style = props.get(style_key)
        assert style, f"{style_key} not set — table falls back to light theme"
        assert "backgroundColor" in style and "color" in style
