"""Routing tests for the season-paged explorer.

All view state lives in the URL: chart clicks and pager buttons write to
`dcc.Location`; a second callback reads the URL back to build the page.
That makes the Location component's `refresh` setting load-bearing.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from dash import dcc
from dash.development.base_component import Component

import app as app_module


def _find_by_id(component: Any, target_id: str) -> Any:
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
def fire(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Invoke `write_url` as though `trigger` caused it."""

    def _invoke(
        trigger: str,
        *,
        click_data: dict | None = None,
        toggle: list | None = None,
        search_value: str | None = None,
        pathname: str = "/",
        search: str = "",
    ):
        monkeypatch.setattr(
            app_module, "callback_context", SimpleNamespace(triggered_id=trigger)
        )
        return app_module.write_url(
            click_data, None, toggle or [], 1, 1, search_value, None, pathname, search
        )

    return _invoke


def test_location_does_not_refresh_the_page() -> None:
    location = _find_by_id(app_module.app.layout, "url")

    assert isinstance(location, dcc.Location)
    assert getattr(location, "refresh", True) is False, (
        "dcc.Location(id='url') must set refresh=False, or the chart-click "
        "callback's pathname output is discarded by a full page navigation."
    )


def test_default_page_is_the_first_season_in_airing_order(fire: Any) -> None:
    df = app_module._filter_episodes(None, "")

    assert (df["season"].dropna() == app_module.SEASONS[0]).all()
    # Airing order: the premiere is the first row.
    assert df.iloc[0]["episode"] == 1


def test_chart_click_jumps_to_the_episode_selected(fire: Any) -> None:
    pathname, search = fire(
        "season-chart",
        click_data={
            "points": [
                {"customdata": {"season": 5, "category": "mythology", "id": "s05e02"}}
            ]
        },
    )

    assert pathname == "/season/5"
    assert "selected=s05e02" in search


def test_pager_steps_between_seasons_and_clamps_at_the_ends(fire: Any) -> None:
    assert fire("season-next", pathname="/season/5")[0] == "/season/6"
    assert fire("season-prev", pathname="/season/5")[0] == "/season/4"
    assert fire("season-prev", pathname=f"/season/{app_module.SEASONS[0]}")[0] == (
        f"/season/{app_module.SEASONS[0]}"
    )
    assert fire("season-next", pathname=f"/season/{app_module.SEASONS[-1]}")[0] == (
        f"/season/{app_module.SEASONS[-1]}"
    )


def test_pager_drops_the_selection_but_keeps_filters(fire: Any) -> None:
    _, search = fire(
        "season-next", pathname="/season/5", search="?selected=s05e02&contested=1"
    )

    assert "selected" not in search
    assert "contested=1" in search


def test_films_appear_on_the_season_page_they_follow() -> None:
    ftf_page = app_module.FILM_PAGE["film-1998"]
    iwtb_page = app_module.FILM_PAGE["film-2008"]

    ftf_df = app_module._filter_episodes(f"/season/{ftf_page}", "")
    assert "film-1998" in set(ftf_df["id"])
    # Airing order puts the film after the finale it followed.
    assert ftf_df.iloc[-1]["id"] == "film-1998"

    iwtb_df = app_module._filter_episodes(f"/season/{iwtb_page}", "")
    assert "film-2008" in set(iwtb_df["id"])


def test_search_writes_the_text_param_and_deselects(fire: Any) -> None:
    _, search = fire(
        "search-input",
        search_value="squeeze",
        pathname="/season/1",
        search="?selected=s01e01",
    )

    assert "text=squeeze" in search
    assert "selected" not in search


def test_contested_filter_matches_the_page_count() -> None:
    """?contested=1 returns exactly the contested records of the page."""
    season = 9
    page = app_module._filter_episodes(f"/season/{season}", "")
    expected = int(page["label_contested"].sum())

    filtered = app_module._filter_episodes(f"/season/{season}", "?contested=1")

    assert expected > 0
    assert len(filtered) == expected
    assert filtered["label_contested"].all()
    # The Truth two-parter is 2-1 contested mythology — it must be here.
    assert (filtered["title"] == "The Truth").sum() == 2
