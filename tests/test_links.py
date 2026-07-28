from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from spooky.links import imdb_url, tmdb_watch_url

# The three shapes a JSON `null` takes once it has been through pandas.
MISSING: list[Any] = [None, float("nan"), pd.NA]


def test_imdb_url_builds_title_link() -> None:
    assert imdb_url("tt0751141") == "https://www.imdb.com/title/tt0751141/"


def test_tmdb_watch_url_builds_tv_season_link() -> None:
    assert (
        tmdb_watch_url(season=5, movie_id=None)
        == "https://www.themoviedb.org/tv/4087-the-x-files/season/5/watch"
    )


def test_tmdb_watch_url_builds_movie_link() -> None:
    assert (
        tmdb_watch_url(season=None, movie_id=846)
        == "https://www.themoviedb.org/movie/846-the-x-files/watch"
    )


def test_link_builders_return_none_for_missing_inputs() -> None:
    assert imdb_url(None) is None
    assert tmdb_watch_url(season=None, movie_id=None) is None


@pytest.mark.parametrize("missing", MISSING)
def test_tmdb_watch_url_handles_pandas_nulls(missing: Any) -> None:
    """A film has no season. pandas delivers that as NaN or pd.NA, not None.

    `int(pd.NA)` raises TypeError, so a bare `is not None` guard crashes on
    every film — and films are first-class records (PRD §3.1).
    """
    assert tmdb_watch_url(season=missing, movie_id=missing) is None


@pytest.mark.parametrize("missing", MISSING)
def test_tmdb_watch_url_builds_movie_link_when_season_is_null(missing: Any) -> None:
    assert (
        tmdb_watch_url(season=missing, movie_id=846)
        == "https://www.themoviedb.org/movie/846-the-x-files/watch"
    )


@pytest.mark.parametrize("missing", MISSING)
def test_imdb_url_handles_pandas_nulls(missing: Any) -> None:
    assert imdb_url(missing) is None
