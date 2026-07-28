from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

_CATEGORIES = [
    ("mythology", "Mythology", "#4E79A7"),
    ("monster-of-the-week", "Monster-of-the-Week", "#F28E2B"),
    ("standalone", "Standalone", "#59A14F"),
]


def build_season_chart(df: pd.DataFrame) -> go.Figure:
    episodes = df[df["season"].notna()].copy()
    seasons = sorted(episodes["season"].astype(int).unique().tolist())

    fig = go.Figure()
    for category_key, category_name, color in _CATEGORIES:
        counts = (
            episodes[episodes["label_derived"] == category_key]
            .groupby("season")
            .size()
            .reindex(seasons, fill_value=0)
        )
        fig.add_bar(
            x=seasons,
            y=counts.tolist(),
            name=category_name,
            marker_color=color,
            customdata=[
                {"season": int(season), "category": category_key} for season in seasons
            ],
            hovertemplate=(
                f"Season %{{x}}<br>{category_name}: %{{y}} episodes<extra></extra>"
            ),
        )

    fig.update_layout(
        barmode="stack",
        template="plotly_dark",
        xaxis_title="Season",
        yaxis_title="Episodes",
        legend_title_text="Category",
        margin={"l": 48, "r": 24, "t": 24, "b": 48},
    )
    fig.update_xaxes(type="category")
    return fig
