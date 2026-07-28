from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from components.chart import build_season_chart


def test_build_season_chart_returns_three_named_traces(
    episodes_df: pd.DataFrame,
) -> None:
    fig = build_season_chart(episodes_df)

    assert isinstance(fig, go.Figure)
    assert [trace.name for trace in fig.data] == [
        "Mythology",
        "Monster-of-the-Week",
        "Standalone",
    ]


def test_chart_palette_is_the_audited_colorblind_safe_trio(
    episodes_df: pd.DataFrame,
) -> None:
    """Okabe-Ito colors, audited in tools/audit_colors.py: pairwise ΔE ≥ 48.9
    under simulated protanopia and deuteranopia, ≥ 5.4:1 against the page
    background. Changing them means re-running the audit (TASKS H-02)."""
    fig = build_season_chart(episodes_df)

    assert [trace.marker.color for trace in fig.data] == [
        "#56B4E9",
        "#E69F00",
        "#009E73",
    ]


def test_build_season_chart_excludes_films(episodes_df: pd.DataFrame) -> None:
    film = episodes_df.iloc[0].copy()
    film["id"] = "film-1998"
    film["title"] = "The X-Files: Fight the Future"
    film["season"] = pd.NA
    film["episode"] = pd.NA
    film["label_derived"] = "mythology"
    df_with_film = pd.concat([episodes_df, film.to_frame().T], ignore_index=True)

    fig = build_season_chart(df_with_film)

    mythology_trace = fig.data[0]
    assert sum(mythology_trace.y) == 4
