from __future__ import annotations

from typing import Any

from dash import html

from spooky.links import imdb_url, tmdb_watch_url
from spooky.values import as_int, is_missing

# A source label that is absent means the source does not cover this record at
# all — the Fox "Mythology" DVD sets predate the revival by a decade. That is
# not the same as the source covering it and declining to list it.
_NO_DATA = "no data"


def build_detail_panel(record: dict[str, Any] | None) -> html.Div:
    if record is None:
        return html.Div("Select an episode", id="detail-panel", className="detail-panel")

    links = _build_links(record)
    children = [
        html.H2(str(record["title"])),
        html.Div(_format_position(record), className="episode-position"),
        html.P(str(record["logline"]), className="logline"),
        html.Div(str(record["review_status"]), className="review-status"),
        html.Dl(
            [
                html.Dt("Air date"),
                html.Dd(_format_air_date(record.get("air_date"))),
                html.Dt("Production code"),
                html.Dd(str(record.get("production_code") or "Unknown")),
                html.Dt("Category"),
                html.Dd(str(record["category"])),
                html.Dt("Director"),
                html.Dd(_join_people(record.get("director", []))),
                html.Dt("Writers"),
                html.Dd(_join_people(record.get("writers", []))),
                html.Dt("Guest cast"),
                html.Dd(_join_people(record.get("guest_cast", []))),
                html.Dt("TVmaze rating"),
                html.Dd(str(record.get("rating") or "Unrated")),
            ]
        ),
    ]
    if bool(record.get("label_contested")):
        children.append(_source_breakdown(record))
    children.append(html.Div(links, className="detail-links"))
    return html.Div(children, id="detail-panel", className="detail-panel")


def _build_links(record: dict[str, Any]) -> list[html.A]:
    imdb = imdb_url(record.get("imdb_id"))
    tmdb = tmdb_watch_url(
        season=record.get("season"),
        movie_id=record.get("tmdb_movie_id"),
    )
    links = []
    if imdb:
        links.append(html.A("IMDb", href=imdb, target="_blank", rel="noreferrer"))
    if tmdb:
        links.append(
            html.A("Where to watch", href=tmdb, target="_blank", rel="noreferrer")
        )
    return links


def _format_position(record: dict[str, Any]) -> str:
    season = as_int(record.get("season"))
    episode = as_int(record.get("episode"))
    if season is None or episode is None:
        return "Film"
    return f"Season {season}, Episode {episode}"


def _format_air_date(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _join_people(values: list[str]) -> str:
    return ", ".join(values) if values else "Unknown"


def _format_source_label(value: Any) -> str:
    """Render one source's verdict for display.

    Missing means the source does not cover this record; `not-listed` means it
    does and did not flag it. Collapsing the two would misrepresent the
    evidence, which is the whole point of showing the breakdown.
    """
    if is_missing(value):
        return _NO_DATA
    return str(value).replace("-", " ")


def _source_breakdown(record: dict[str, Any]) -> html.Div:
    fox = _format_source_label(record.get("label_fox_dvd"))
    wikipedia = _format_source_label(record.get("label_wikipedia"))
    dom111 = _format_source_label(record.get("label_dom111"))
    rationale = record.get("label_rationale")
    return html.Div(
        [
            html.H3("Classification sources"),
            html.P(f"Fox DVDs: {fox} · Wikipedia: {wikipedia} · dom111: {dom111}"),
            html.P("" if is_missing(rationale) else str(rationale)),
        ],
        className="source-breakdown",
    )
