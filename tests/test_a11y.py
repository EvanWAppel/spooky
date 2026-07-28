"""Accessibility tests (TASKS H-05, H-08).

The chart's screen-reader alternative must carry the same numbers the
stacked bars encode, and the /about view must name all three label sources.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import pandas as pd
from dash import html

from components.about import build_about
from components.chart import build_season_summary_table


def _rows(table: html.Table) -> list[Any]:
    # Dash's generated stubs type `children` as None-able and attribute-less;
    # cast once so the assertions below stay readable.
    children = cast(Any, table).children
    tbody = next(c for c in children if isinstance(c, html.Tbody))
    return list(cast(Any, tbody).children)


def test_summary_table_is_visually_hidden_but_present(
    episodes_df: pd.DataFrame,
) -> None:
    table = cast(Any, build_season_summary_table(episodes_df))

    assert table.className == "sr-only"
    assert isinstance(table.children[0], html.Caption)


def test_summary_table_counts_match_the_data(episodes_df: pd.DataFrame) -> None:
    table = build_season_summary_table(episodes_df)
    rows = _rows(table)

    episodes = episodes_df[episodes_df["season"].notna()]
    seasons = sorted(episodes["season"].astype(int).unique())
    assert len(rows) == len(seasons)

    # Every row's per-category cells must sum to its Total cell.
    for row in rows:
        cells = [int(td.children) for td in row.children[1:]]
        *categories, total = cells
        assert sum(categories) == total


def test_summary_table_totals_match_the_corpus(episodes_df: pd.DataFrame) -> None:
    table = build_season_summary_table(episodes_df)
    rows = _rows(table)

    grand_total = sum(int(row.children[-1].children) for row in rows)
    assert grand_total == int(episodes_df["season"].notna().sum())


def test_about_names_all_three_label_sources(
    render_text: Callable[[Any], str],
) -> None:
    rendered = render_text(build_about())

    assert "Fox" in rendered
    assert "Wikipedia" in rendered
    assert "dom111" in rendered
    # And explains the two load-bearing concepts.
    assert "abstain" in rendered.lower()
    assert "Contested" in rendered
