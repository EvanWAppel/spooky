from __future__ import annotations

from typing import Any, cast

import pandas as pd
from dash import dash_table

_COLUMNS = cast(
    Any,
    [
        {"name": "Season/Ep", "id": "season_episode"},
        {"name": "Title", "id": "title"},
        {"name": "Type", "id": "record_type"},
        {"name": "Air date", "id": "air_date"},
        {"name": "Category", "id": "category"},
        {"name": "TVmaze rating", "id": "rating"},
        {"name": "Contested", "id": "contested_badge"},
    ],
)

# The DataTable does not inherit the page's CSS — without explicit style
# props it renders its default light theme on the dark page (near-invisible
# gray-on-white). Palette matches assets/styles.css.
_BG = "#111417"
_BG_HEADER = "#1a2019"
_FG = "#f1f5f2"
_FG_MUTED = "#9aa8a0"
_BORDER = "#26302b"

_STYLE_HEADER = {
    "backgroundColor": _BG_HEADER,
    "color": _FG,
    "fontWeight": "600",
    "borderBottom": f"1px solid {_BORDER}",
}
_STYLE_CELL = {
    "backgroundColor": _BG,
    "color": _FG,
    "border": "none",
    "borderBottom": f"1px solid {_BORDER}",
    "padding": "8px 12px",
    "fontFamily": "inherit",
    "fontSize": "0.95rem",
    "textAlign": "left",
}
_STYLE_DATA_CONDITIONAL = [
    {
        "if": {
            "column_id": "contested_badge",
            "filter_query": "{contested_badge} ne ''",
        },
        "color": "#f2b84b",
        "fontWeight": "600",
    },
    {
        "if": {"column_id": "record_type", "filter_query": "{record_type} eq 'Film'"},
        "color": "#7fd4a0",
        "fontWeight": "600",
    },
    {"if": {"state": "active"}, "backgroundColor": "#1f2a24", "border": "none"},
    {"if": {"state": "selected"}, "backgroundColor": "#1f2a24", "border": "none"},
    {"if": {"column_id": "rating"}, "fontVariantNumeric": "tabular-nums"},
]


def build_episode_table(df: pd.DataFrame) -> dash_table.DataTable:
    """The episode list: variable length, sorted by air order.

    Pagination and per-column filter boxes are deliberately OFF — the page
    is one season (the pager and search input outside the table drive the
    view), so the table shows every row it is given. Native sort stays.
    """
    table_df = df.copy()
    table_df["air_date"] = table_df["air_date"].dt.strftime("%Y-%m-%d")
    table_df["contested_badge"] = table_df["label_contested"].map(
        {True: "Contested", False: ""}
    )
    table_df["record_type"] = table_df["season"].map(
        lambda value: "Episode" if pd.notna(value) else "Film"
    )

    return dash_table.DataTable(
        id="episode-table",
        columns=_COLUMNS,
        data=table_df[
            [
                "id",
                "season_episode",
                "title",
                "record_type",
                "air_date",
                "category",
                "rating",
                "contested_badge",
            ]
        ].to_dict("records"),
        sort_action="native",
        filter_action="none",
        row_selectable=False,
        cell_selectable=True,
        page_action="none",
        style_as_list_view=True,
        style_header=_STYLE_HEADER,
        style_cell=_STYLE_CELL,
        style_data_conditional=cast(Any, _STYLE_DATA_CONDITIONAL),
        style_table={"overflowX": "auto"},
    )
