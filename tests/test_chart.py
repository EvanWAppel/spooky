from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from components.chart import build_season_chart

OKABE_ITO = ["#56B4E9", "#E69F00", "#009E73"]


def test_legend_shows_the_three_categories_in_order(
    episodes_df: pd.DataFrame,
) -> None:
    fig = build_season_chart(episodes_df)

    legend_traces = [trace for trace in fig.data if trace.showlegend]
    assert isinstance(fig, go.Figure)
    assert [trace.name for trace in legend_traces] == [
        "Mythology",
        "Monster-of-the-Week",
        "Standalone",
    ]


def test_chart_palette_is_the_audited_colorblind_safe_trio(
    episodes_df: pd.DataFrame,
) -> None:
    """Okabe-Ito colors, audited in tools/audit_colors.py: pairwise ΔE ≥ 48.9
    under simulated protanopia and deuteranopia. Changing them means
    re-running the audit (TASKS H-02)."""
    fig = build_season_chart(episodes_df)

    legend_traces = [trace for trace in fig.data if trace.showlegend]
    assert [trace.marker.color for trace in legend_traces] == OKABE_ITO


def _episode_trace(fig: go.Figure):
    return next(trace for trace in fig.data if trace.name == "episodes")


def test_one_block_per_episode_in_airing_order(episodes_df: pd.DataFrame) -> None:
    """Each season's bar stacks its episodes oldest-at-bottom: the premiere
    has base 0 and bases increase with episode number."""
    fig = build_season_chart(episodes_df)
    trace = _episode_trace(fig)

    episode_count = int(episodes_df["season"].notna().sum())
    assert len(trace.x) == episode_count
    assert all(y == 1 for y in trace.y)

    by_season: dict[int, list[float]] = {}
    for season, base in zip(trace.x, trace.base, strict=True):
        by_season.setdefault(int(season), []).append(base)
    for season, bases in by_season.items():
        assert bases == sorted(bases), f"season {season} out of airing order"
        assert bases[0] == 0, f"season {season} premiere not at the bottom"


def test_blocks_are_colored_by_category(episodes_df: pd.DataFrame) -> None:
    fig = build_season_chart(episodes_df)
    trace = _episode_trace(fig)

    color_by_key = dict(
        zip(["mythology", "monster-of-the-week", "standalone"], OKABE_ITO, strict=True)
    )
    ordered = episodes_df[episodes_df["season"].notna()].sort_values(
        ["season", "episode"]
    )
    expected = [color_by_key[key] for key in ordered["label_derived"]]
    assert list(trace.marker.color) == expected


def test_click_payload_carries_the_episode_id(episodes_df: pd.DataFrame) -> None:
    fig = build_season_chart(episodes_df)
    trace = _episode_trace(fig)

    first = trace.customdata[0]
    assert set(first) == {"season", "category", "id"}
    assert first["id"].startswith("s")


def test_variant_tagline_blocks_glow(episodes_df: pd.DataFrame) -> None:
    """A block whose episode has a changed opening tagline gets the bright glow
    outline; every other block keeps the thin dark separator."""
    df = episodes_df.copy()
    target_id = df.loc[df["season"].notna(), "id"].iloc[0]
    df.loc[df["id"] == target_id, "tagline_is_variant"] = True

    trace = _episode_trace(build_season_chart(df))
    colors = list(trace.marker.line.color)
    widths = list(trace.marker.line.width)

    glow_idx = [i for i, c in enumerate(colors) if c == "#FFE9A8"]
    assert len(glow_idx) == 1, "exactly the one variant block should glow"
    i = glow_idx[0]
    assert trace.customdata[i]["id"] == target_id
    assert widths[i] > 0.5
    assert all(colors[j] == "#111417" for j in range(len(colors)) if j != i)


def test_no_blocks_glow_when_no_taglines_vary(episodes_df: pd.DataFrame) -> None:
    """The sample corpus has no variant taglines — nothing glows."""
    trace = _episode_trace(build_season_chart(episodes_df))
    assert all(color == "#111417" for color in trace.marker.line.color)


def test_build_season_chart_excludes_films(episodes_df: pd.DataFrame) -> None:
    film = episodes_df.iloc[0].copy()
    film["id"] = "film-1998"
    film["title"] = "The X-Files: Fight the Future"
    film["season"] = pd.NA
    film["episode"] = pd.NA
    film["label_derived"] = "mythology"
    df_with_film = pd.concat([episodes_df, film.to_frame().T], ignore_index=True)

    fig = build_season_chart(df_with_film)

    assert len(_episode_trace(fig).x) == int(episodes_df["season"].notna().sum())
