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
