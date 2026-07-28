from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import html

# Okabe-Ito colors — audited colorblind-safe in tools/audit_colors.py
# (pairwise ΔE ≥ 48.9 under simulated protanopia and deuteranopia, and
# ≥ 5.4:1 contrast against the #111417 page background). Re-run the audit
# before changing any of these (TASKS H-02).
_CATEGORIES = [
    ("mythology", "Mythology", "#56B4E9"),
    ("monster-of-the-week", "Monster-of-the-Week", "#E69F00"),
    ("standalone", "Standalone", "#009E73"),
]


def _season_counts(df: pd.DataFrame) -> tuple[list[int], dict[str, list[int]]]:
    episodes = df[df["season"].notna()]
    seasons = sorted(episodes["season"].astype(int).unique().tolist())
    counts = {}
    for category_key, _name, _color in _CATEGORIES:
        series = (
            episodes[episodes["label_derived"] == category_key]
            .groupby("season")
            .size()
            .reindex(seasons, fill_value=0)
        )
        counts[category_key] = [int(v) for v in series.tolist()]
    return seasons, counts


def build_season_chart(df: pd.DataFrame) -> go.Figure:
    seasons, counts = _season_counts(df)

    fig = go.Figure()
    for category_key, category_name, color in _CATEGORIES:
        fig.add_bar(
            x=seasons,
            y=counts[category_key],
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
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Season",
        yaxis_title="Episodes",
        legend_title_text="Category",
        margin={"l": 48, "r": 24, "t": 24, "b": 48},
        height=420,
    )
    fig.update_xaxes(type="category")
    return fig


def build_season_summary_table(df: pd.DataFrame) -> html.Table:
    """Screen-reader alternative to the chart (TASKS H-05).

    Visually hidden via the ``sr-only`` class; carries the same per-season
    counts the stacked bars encode.
    """
    seasons, counts = _season_counts(df)
    header = html.Tr(
        [html.Th("Season")]
        + [html.Th(name) for _key, name, _color in _CATEGORIES]
        + [html.Th("Total")]
    )
    rows = []
    for index, season in enumerate(seasons):
        values = [counts[key][index] for key, _n, _c in _CATEGORIES]
        rows.append(
            html.Tr(
                [html.Th(f"Season {season}", scope="row")]
                + [html.Td(str(value)) for value in values]
                + [html.Td(str(sum(values)))]
            )
        )
    return html.Table(
        [
            html.Caption(
                "Episodes per season by classification: mythology, "
                "monster-of-the-week, and standalone."
            ),
            html.Thead(header),
            html.Tbody(rows),
        ],
        className="sr-only",
    )
