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
        tagline: list | None = None,
        search_value: str | None = None,
        pathname: str = "/",
        search: str = "",
    ):
        monkeypatch.setattr(
            app_module, "callback_context", SimpleNamespace(triggered_id=trigger)
        )
        return app_module.write_url(
            click_data,
            None,
            toggle or [],
            tagline or [],
            1,
            1,
            search_value,
            None,
            pathname,
            search,
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


def test_tagline_toggle_writes_the_variant_param(fire: Any) -> None:
    """T-09: the toggle round-trips ?tagline=variant, and clears it."""
    _, on = fire("tagline-toggle", tagline=["tagline"], pathname="/season/1")
    assert "tagline=variant" in on

    _, off = fire(
        "tagline-toggle", tagline=[], pathname="/season/1", search="?tagline=variant"
    )
    assert "tagline" not in off


def test_tagline_filter_matches_the_page_variant_count() -> None:
    """T-09: ?tagline=variant returns exactly the variant records of the page."""
    season = 4  # Herrenvolk, Teliko, Terma, Gethsemane all live here
    page = app_module._filter_episodes(f"/season/{season}", "")
    expected = int(page["tagline_is_variant"].sum())

    filtered = app_module._filter_episodes(f"/season/{season}", "?tagline=variant")

    assert expected > 0
    assert len(filtered) == expected
    assert filtered["tagline_is_variant"].all()


def test_taglines_catalogue_lists_every_variant_and_links_to_it() -> None:
    """T-10: the /taglines view lists exactly the variant episodes, each linked."""
    from components.taglines_view import build_taglines_view

    view = build_taglines_view(app_module.EPISODES)
    variants = app_module.EPISODES[app_module.EPISODES["tagline_is_variant"]]
    links = _collect_links(view)
    hrefs = {href for _, href in links}
    for record_id in variants["id"]:
        assert any(f"selected={record_id}" in href for href in hrefs), record_id
    # A row per variant, and the famous first swap is present by text.
    texts = " ".join(text for text, _ in links)
    assert "The Erlenmeyer Flask" in texts


def _collect_links(component: Any) -> list[tuple[str, str]]:
    """(text, href) for every dcc.Link in a component tree."""
    found: list[tuple[str, str]] = []
    if isinstance(component, dcc.Link):
        children = getattr(component, "children", "")
        text = children if isinstance(children, str) else str(children)
        found.append((text, getattr(component, "href", "")))
    if isinstance(component, Component):
        children = getattr(component, "children", None)
        if children is not None:
            found.extend(_collect_links(children))
    if isinstance(component, list | tuple):
        for child in component:
            found.extend(_collect_links(child))
    return found


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
