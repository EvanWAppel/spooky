from __future__ import annotations

import pandas as pd
from dash import html

from spooky.links import imdb_url, tmdb_watch_url
from spooky.values import is_missing


def build_films_card(df: pd.DataFrame) -> html.Section | None:
    """The two feature films, outside the season chart (PRD §3.1)."""
    films = df[df["season"].isna()]
    if films.empty:
        return None
    return html.Section(
        [
            html.H2("The films"),
            html.P(
                "Both features are first-class records — searchable and "
                "classified — but excluded from the season chart so bar "
                "heights mean what they appear to mean.",
                className="films-note",
            ),
            html.Ul(
                [_film_item(row) for _, row in films.iterrows()],
                className="films-list",
            ),
        ],
        className="films-card",
    )


def _film_item(row: pd.Series) -> html.Li:
    year = row["air_date"].year if not is_missing(row["air_date"]) else ""
    badges = [html.Span(str(row["category"]), className="category-badge")]
    if bool(row["label_contested"]):
        badges.append(html.Span("Contested", className="contested-badge"))
    links = []
    imdb = imdb_url(row["imdb_id"])
    if imdb:
        links.append(html.A("IMDb", href=imdb, target="_blank", rel="noreferrer"))
    watch = tmdb_watch_url(season=None, movie_id=row["tmdb_movie_id"])
    if watch:
        links.append(
            html.A("Where to watch", href=watch, target="_blank", rel="noreferrer")
        )
    return html.Li(
        [
            html.Strong(f"{row['title']} ({year})"),
            html.Span(badges, className="film-badges"),
            html.Span(links, className="film-links"),
        ],
        className="film-item",
    )
