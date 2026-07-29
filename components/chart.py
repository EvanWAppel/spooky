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
_COLOR = {key: color for key, _n, color in _CATEGORIES}
_NAME = {key: name for key, name, _c in _CATEGORIES}


def _episodes_in_air_order(df: pd.DataFrame) -> pd.DataFrame:
    episodes = df[df["season"].notna()].copy()
    episodes["season"] = episodes["season"].astype(int)
    episodes["episode"] = episodes["episode"].astype(int)
    return episodes.sort_values(["season", "episode"])


def build_season_chart(df: pd.DataFrame) -> go.Figure:
    """One block per episode, stacked per season in airing order.

    The season premiere sits at the bottom of its bar and the finale at the
    top; each block is colored by the episode's derived classification.
    """
    episodes = _episodes_in_air_order(df)
    positions = episodes.groupby("season").cumcount()

    fig = go.Figure()
    # Legend proxies: the real trace is one bar per episode, so the legend
    # entries are drawn from three empty stand-ins in category order.
    for _key, name, color in _CATEGORIES:
        fig.add_bar(x=[None], y=[None], name=name, marker_color=color, showlegend=True)

    seasons = [int(v) for v in episodes["season"]]
    numbers = [int(v) for v in episodes["episode"]]
    labels = list(episodes["label_derived"])
    titles = list(episodes["title"])
    ids = list(episodes["id"])

    fig.add_bar(
        x=seasons,
        y=[1] * len(episodes),
        base=positions.tolist(),
        marker_color=[_COLOR[key] for key in labels],
        marker_line={"width": 0.5, "color": "#111417"},
        customdata=[
            {"season": season, "category": label, "id": record_id}
            for season, label, record_id in zip(seasons, labels, ids, strict=True)
        ],
        hovertext=[
            f"S{season:02d}E{number:02d} {title} — {_NAME[label]}"
            for season, number, title, label in zip(
                seasons, numbers, titles, labels, strict=True
            )
        ],
        hovertemplate="%{hovertext}<extra></extra>",
        showlegend=False,
        name="episodes",
    )

    fig.update_layout(
        barmode="overlay",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Season",
        yaxis_title="Episodes, in airing order",
        legend_title_text="Category",
        margin={"l": 48, "r": 24, "t": 24, "b": 48},
        height=440,
    )
    fig.update_xaxes(type="category")
    return fig


def build_season_summary_table(df: pd.DataFrame) -> html.Table:
    """Screen-reader alternative to the chart (TASKS H-05).

    Visually hidden via the ``sr-only`` class; carries the same per-season
    counts the stacked blocks encode.
    """
    episodes = _episodes_in_air_order(df)
    seasons = sorted(episodes["season"].unique().tolist())
    header = html.Tr(
        [html.Th("Season")]
        + [html.Th(name) for _key, name, _color in _CATEGORIES]
        + [html.Th("Total")]
    )
    rows = []
    for season in seasons:
        in_season = episodes[episodes["season"] == season]
        values = [
            int((in_season["label_derived"] == key).sum()) for key, _n, _c in _CATEGORIES
        ]
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
