from __future__ import annotations

from typing import Any, cast

import pandas as pd
from dash import dash_table

_COLUMNS = cast(
    Any,
    [
        {"name": "Season/Ep", "id": "season_episode"},
        {"name": "Title", "id": "title"},
        {"name": "Air date", "id": "air_date"},
        {"name": "Category", "id": "category"},
        {"name": "TVmaze rating", "id": "rating"},
        {"name": "Contested", "id": "contested_badge"},
    ],
)


def build_episode_table(df: pd.DataFrame) -> dash_table.DataTable:
    table_df = df.copy()
    table_df["air_date"] = table_df["air_date"].dt.strftime("%Y-%m-%d")
    table_df["contested_badge"] = table_df["label_contested"].map(
        {True: "Contested", False: ""}
    )

    return dash_table.DataTable(
        id="episode-table",
        columns=_COLUMNS,
        data=table_df[
            [
                "id",
                "season_episode",
                "title",
                "air_date",
                "category",
                "rating",
                "contested_badge",
            ]
        ].to_dict("records"),
        sort_action="native",
        filter_action="native",
        row_selectable=False,
        cell_selectable=True,
        page_action="native",
        page_size=12,
        style_as_list_view=True,
    )
