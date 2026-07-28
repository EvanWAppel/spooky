"""Routing tests for the chart-click → URL → table pipeline (TASKS C-15/C-16/C-17).

The app drives all view state through the URL: a click writes to `dcc.Location`,
and a separate callback reads the URL back to filter the table. That makes the
Location component's `refresh` setting load-bearing, not cosmetic.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from dash import dcc
from dash.development.base_component import Component

import app as app_module


def _find_by_id(component: Any, target_id: str) -> Any:
    """Depth-first search of a Dash layout tree for a component by id."""
    if isinstance(component, Component):
        if getattr(component, "id", None) == target_id:
            return component
        children = getattr(component, "children", None)
        if children is not None:
            found = _find_by_id(children, target_id)
            if found is not None:
                return found
    if isinstance(component, list | tuple):
        for child in component:
            found = _find_by_id(child, target_id)
            if found is not None:
                return found
    return None


@pytest.fixture
def chart_click(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Invoke `write_url` as though the season chart was the trigger."""

    def _invoke(click_data: dict[str, Any], pathname: str = "/", search: str = ""):
        monkeypatch.setattr(
            app_module,
            "callback_context",
            SimpleNamespace(triggered_id="season-chart"),
        )
        return app_module.write_url(click_data, None, [], None, pathname, search)

    return _invoke


def test_location_does_not_refresh_the_page() -> None:
    """`refresh=True` makes a pathname+search write lose the pathname.

    Dash defaults `refresh` to True, which performs a real browser navigation.
    When one callback writes both `pathname` and `search`, that navigation
    discards the pathname and only the query string survives — so clicking a
    season's category segment filters by category across *all* seasons.
    """
    location = _find_by_id(app_module.app.layout, "url")

    assert isinstance(location, dcc.Location)
    # Unset means Dash's default of True, which is the bug.
    assert getattr(location, "refresh", True) is False, (
        "dcc.Location(id='url') must set refresh=False, or the chart-click "
        "callback's pathname output is discarded by a full page navigation."
    )


def test_chart_click_writes_both_season_and_category(chart_click: Any) -> None:
    """Clicking a stacked segment must filter to that season AND category."""
    pathname, search = chart_click(
        {"points": [{"x": 5, "customdata": {"season": 5, "category": "mythology"}}]}
    )

    assert pathname == "/season/5"
    assert "category=mythology" in search


def test_chart_click_then_filter_returns_only_that_season(chart_click: Any) -> None:
    """End-to-end through the real filter: season AND category both apply.

    Expectations derive from the loaded corpus rather than hard-coded
    titles, so the test holds for the real 220-record dataset.
    """
    pathname, search = chart_click(
        {"points": [{"x": 5, "customdata": {"season": 5, "category": "mythology"}}]}
    )
    filtered = app_module._filter_episodes(pathname, search)

    corpus = app_module.EPISODES
    expected = corpus[(corpus["season"] == 5) & (corpus["label_derived"] == "mythology")]
    assert len(filtered) == len(expected) > 0
    assert (filtered["season"] == 5).all()
    assert (filtered["label_derived"] == "mythology").all()
    assert "Redux II" in set(filtered["title"])


def test_chart_click_falls_back_to_point_x_without_customdata(
    chart_click: Any,
) -> None:
    """Plotly does not always round-trip dict customdata; `x` is the fallback."""
    pathname, _ = chart_click({"points": [{"x": 10}]})

    assert pathname == "/season/10"


def test_contested_filter_matches_the_corpus_count() -> None:
    """G-04: ?contested=1 returns exactly the contested records."""
    corpus = app_module.EPISODES
    expected = int(corpus["label_contested"].sum())

    filtered = app_module._filter_episodes(None, "?contested=1")

    assert expected > 0
    assert len(filtered) == expected
    assert filtered["label_contested"].all()


def test_contested_filter_composes_with_season_and_category() -> None:
    filtered = app_module._filter_episodes("/season/9", "?contested=1")

    assert (filtered["season"] == 9).all()
    assert filtered["label_contested"].all()
    # The Truth two-parter is 2-1 contested mythology — it must be here.
    assert (filtered["title"] == "The Truth").sum() == 2
