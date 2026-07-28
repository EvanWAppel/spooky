from __future__ import annotations

from typing import Any

from spooky.values import as_int, is_missing


def imdb_url(imdb_id: str | None) -> str | None:
    if is_missing(imdb_id) or not imdb_id:
        return None
    return f"https://www.imdb.com/title/{imdb_id}/"


def tmdb_watch_url(season: Any, movie_id: Any) -> str | None:
    """Films link to their TMDB movie watch page; episodes to the show's.

    Verified live (TASKS G-05): TMDB has no season-level watch pages —
    ``/season/N/watch`` 404s — so every episode links to the show-level
    ``/watch`` page, which is sanctioned, provider-agnostic, and updates
    itself when the show moves services.

    `season` and `movie_id` arrive from pandas, so they may be NaN or pd.NA
    rather than None — `is None` is not a sufficient guard here.
    """
    movie = as_int(movie_id)
    if movie is not None:
        return f"https://www.themoviedb.org/movie/{movie}-the-x-files/watch"

    if as_int(season) is not None:
        return "https://www.themoviedb.org/tv/4087-the-x-files/watch"
    return None
