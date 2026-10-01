from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode

import pandas as pd
from dash import Dash, Input, Output, State, callback_context, dcc, html
from flask import Response, abort

from components.about import build_about
from components.chart import build_season_chart, build_season_summary_table
from components.panel import build_detail_panel
from components.provenance_view import build_provenance_view
from components.ssr import (
    render_episode,
    render_index,
    render_provenance,
    render_season,
    render_sitemap,
    robots_txt,
)
from components.table import _STYLE_DATA_CONDITIONAL, build_episode_table
from components.taglines_view import build_taglines_view
from spooky.loader import load_episodes
from spooky.logging_config import setup_logging
from spooky.search import build_index
from spooky.search import search as fts_search

setup_logging()

EPISODES = load_episodes(Path(__file__).resolve().parent / "data" / "episodes")

# Full-text index built in memory from the JSON source of truth at startup —
# never a committed *.sqlite (CLAUDE.md). Drives the ?text= search (Group R.1).
SEARCH_INDEX = build_index(EPISODES)

SEASONS: list[int] = sorted(
    EPISODES.loc[EPISODES["season"].notna(), "season"].astype(int).unique().tolist()
)


def _assign_film_pages() -> dict[str, int]:
    """Films live on the season page they follow chronologically.

    Fight the Future (1998) lands after the season 5 finale; I Want to
    Believe (2008) after season 9. Derived from air dates, never hard-coded.
    """
    pages: dict[str, int] = {}
    episodes = EPISODES[EPISODES["season"].notna()]
    for _, film in EPISODES[EPISODES["season"].isna()].iterrows():
        earlier = episodes[episodes["air_date"] < film["air_date"]]
        if earlier.empty:
            pages[film["id"]] = SEASONS[0]
        else:
            latest = earlier.loc[earlier["air_date"].idxmax()]
            pages[film["id"]] = int(latest["season"])
    return pages


FILM_PAGE = _assign_film_pages()

# Wildcard aria-* props are legal on Dash HTML components at runtime but
# absent from the generated stubs — routed through a typed-as-Any dict so
# ty stays clean without an ignore comment.
_CHART_ARIA: dict[str, Any] = {
    "aria-label": (
        "One block per episode, stacked by season in airing order and "
        "colored by classification. A data table with per-season counts "
        "follows."
    )
}

_DECORATIVE_ARIA: dict[str, Any] = {"aria-hidden": "true"}

app = Dash(__name__, title="spooky")
server = app.server
app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <noscript>
            Episode metadata and ratings from TVmaze, licensed CC BY-SA 4.0.
            Additional episode data derived from Wikipedia, licensed CC BY-SA 4.0;
            modified. Identifier data from Wikidata (CC0). Mythology/monster-of-the-week
            labels adapted from dom111/xfiles-episode-picker (MIT). The derived dataset
            published here is licensed CC BY-SA 4.0.
            This is an unofficial fan project. It is not affiliated with, endorsed by,
            or approved by 20th Television, The Walt Disney Company, or Ten Thirteen
            Productions. The X-Files and all related marks are the property of their
            respective owners. Contact: appelew@gmail.com
            This website uses TMDB and the TMDB APIs but is not endorsed, certified,
            or otherwise approved by TMDB.
        </noscript>
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""


def _current_season(pathname: str | None) -> int:
    """The season page in view; defaults to the first season."""
    if pathname and pathname.startswith("/season/"):
        season_text = pathname.removeprefix("/season/").split("/", maxsplit=1)[0]
        if season_text.isdigit() and int(season_text) in SEASONS:
            return int(season_text)
    return SEASONS[0]


def _filter_episodes(pathname: str | None, search: str | None) -> pd.DataFrame:
    """One season page — its episodes plus any film that follows it — with
    the search/category/contested filters applied, in airing order."""
    season = _current_season(pathname)
    params = parse_qs((search or "").lstrip("?"))
    text = params.get("text", [None])[0]

    if text:
        # Full-text search is site-wide (all 220 records), ranked by relevance,
        # over titles + loglines — not the season-scoped substring-on-title it
        # replaces. Preserve the bm25 order the index returns (Group R.1).
        ranked = fts_search(SEARCH_INDEX, text)
        rank = {record_id: position for position, record_id in enumerate(ranked)}
        df = EPISODES[EPISODES["id"].isin(ranked)].copy()
        df = df.sort_values("id", key=lambda ids: ids.map(rank))
    else:
        film_ids = [film_id for film_id, page in FILM_PAGE.items() if page == season]
        df = EPISODES[
            (EPISODES["season"] == season) | (EPISODES["id"].isin(film_ids))
        ].sort_values("air_date")

    category = params.get("category", [None])[0]
    if category:
        df = df[df["label_derived"] == category]

    if params.get("contested", [None])[0] == "1":
        df = df[df["label_contested"]]

    if params.get("tagline", [None])[0] == "variant":
        df = df[df["tagline_is_variant"]]

    return df


def _table_data(df: pd.DataFrame):
    return build_episode_table(df).to_plotly_json()["props"]["data"]


def _selected_record(search: str | None, visible_rows: list[dict] | None):
    params = parse_qs((search or "").lstrip("?"))
    selected = params.get("selected", [None])[0]
    if selected:
        rows = EPISODES[EPISODES["id"] == selected]
        if not rows.empty:
            return rows.iloc[0].to_dict()
    if visible_rows:
        first_id = visible_rows[0].get("id")
        rows = EPISODES[EPISODES["id"] == first_id]
        if not rows.empty:
            return rows.iloc[0].to_dict()
    return None


def _category_label(category: str | None) -> str:
    return {
        "mythology": "Mythology",
        "monster-of-the-week": "Monster-of-the-Week",
        "standalone": "Standalone",
    }.get(category or "", "")


def _season_label(season: int) -> str:
    dates = EPISODES.loc[EPISODES["season"] == season, "air_date"]
    years = sorted({d.year for d in dates})
    span = str(years[0]) if len(years) == 1 else f"{years[0]}–{years[-1]}"
    return f"Season {season} · {span}"


def _filter_chip(pathname: str | None, search: str | None) -> html.Div | str:
    params = parse_qs((search or "").lstrip("?"))
    parts = []
    if category := _category_label(params.get("category", [None])[0]):
        parts.append(category)
    if params.get("text", [None])[0]:
        parts.append(f"matching “{params['text'][0]}” across all seasons")
    if params.get("contested", [None])[0] == "1":
        parts.append("contested only")
    if params.get("tagline", [None])[0] == "variant":
        parts.append("variant taglines only")
    if not parts:
        return ""
    clear_href = f"/season/{_current_season(pathname)}"
    return html.Div(
        [
            html.Span(" · ".join(parts)),
            dcc.Link("Clear", href=clear_href, className="clear-filter"),
        ],
        className="filter-chip",
    )


footer = html.Footer(
    [
        html.P(
            [
                "Episode metadata and ratings from ",
                html.A("TVmaze", href="https://www.tvmaze.com"),
                ", licensed ",
                html.A(
                    "CC BY-SA 4.0",
                    href="https://creativecommons.org/licenses/by-sa/4.0/",
                ),
                ". Additional episode data derived from ",
                html.A(
                    "Wikipedia",
                    href="https://en.wikipedia.org/wiki/List_of_The_X-Files_episodes",
                ),
                ", licensed ",
                html.A(
                    "CC BY-SA 4.0",
                    href="https://creativecommons.org/licenses/by-sa/4.0/",
                ),
                "; modified. Identifier data from ",
                html.A("Wikidata", href="https://www.wikidata.org"),
                " (CC0). Mythology/monster-of-the-week labels adapted from ",
                html.A(
                    "dom111/xfiles-episode-picker",
                    href="https://github.com/dom111/xfiles-episode-picker",
                ),
                " (MIT). The derived dataset published here is licensed CC BY-SA 4.0.",
            ]
        ),
        html.P(
            "This is an unofficial fan project. It is not affiliated with, endorsed "
            "by, or approved by 20th Television, The Walt Disney Company, or Ten "
            "Thirteen Productions. The X-Files and all related marks are the property "
            "of their respective owners. Contact: appelew@gmail.com"
        ),
        html.P(
            "This website uses TMDB and the TMDB APIs but is not endorsed, certified, "
            "or otherwise approved by TMDB."
        ),
        html.P(
            [
                html.A("Text-only index", href="/overview"),
                " · ",
                html.A("Sitemap", href="/sitemap.xml"),
            ],
            className="footer-links",
        ),
    ],
    className="site-footer",
)


app.layout = html.Div(
    [
        # refresh=False keeps this a client-side history push. With Dash's
        # default (True), writing pathname and search in one callback triggers a
        # real browser navigation that discards the pathname — a chart click
        # would lose its season. See tests/test_app_routing.py.
        dcc.Location(id="url", refresh=False),
        html.A("Skip to case index", href="#case-index", className="skip-link"),
        html.Header(
            [
                dcc.Link(
                    [
                        html.Span("◉", className="brand-symbol"),
                        "spooky",
                        html.Span("/", className="brand-register"),
                    ],
                    href="/",
                    className="brand",
                ),
                html.Span("AN INDEPENDENT X-FILES ARCHIVE", className="header-caption"),
                html.Nav(
                    [
                        dcc.Link(
                            "01 / Explore",
                            href="/",
                            id="nav-explore",
                            className="nav-link",
                        ),
                        dcc.Link(
                            "02 / Taglines",
                            href="/taglines",
                            id="nav-taglines",
                            className="nav-link",
                        ),
                        dcc.Link(
                            "03 / Provenance",
                            href="/provenance",
                            id="nav-provenance",
                            className="nav-link",
                        ),
                        dcc.Link(
                            "04 / About",
                            href="/about",
                            id="nav-about",
                            className="nav-link",
                        ),
                    ],
                    className="site-nav",
                ),
            ],
            className="site-header",
        ),
        html.Main(
            [
                html.Div(
                    [
                        html.Section(
                            [
                                html.Div(
                                    [
                                        html.P(
                                            "THE X-FILES / FIELD GUIDE",
                                            className="eyebrow",
                                        ),
                                        html.H1(
                                            [
                                                "Follow the",
                                                html.Br(),
                                                html.Em("unexplained."),
                                            ]
                                        ),
                                        html.P(
                                            "Conspiracies. Creatures. "
                                            "Cases that won’t close. "
                                            "Explore the patterns behind every episode "
                                            "of The X-Files.",
                                            className="lede",
                                        ),
                                    ],
                                    className="hero-copy",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Span("ARCHIVE / COMPLETE"),
                                                html.Span("● ONLINE", className="online"),
                                            ],
                                            className="archive-topline",
                                        ),
                                        html.Div(
                                            [html.Span("◎", className="orbit-core")],
                                            className="orbital",
                                            **_DECORATIVE_ARIA,
                                        ),
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.Strong(
                                                            str(
                                                                int(
                                                                    EPISODES["season"]
                                                                    .notna()
                                                                    .sum()
                                                                )
                                                            )
                                                        ),
                                                        html.Span("EPISODES"),
                                                    ]
                                                ),
                                                html.Div(
                                                    [
                                                        html.Strong(
                                                            f"{len(SEASONS):02d}"
                                                        ),
                                                        html.Span("SEASONS"),
                                                    ]
                                                ),
                                                html.Div(
                                                    [
                                                        html.Strong(
                                                            f"{int(EPISODES['season'].isna().sum()):02d}"
                                                        ),
                                                        html.Span("FILMS"),
                                                    ]
                                                ),
                                            ],
                                            className="archive-stats",
                                        ),
                                    ],
                                    className="archive-card",
                                ),
                            ],
                            className="hero",
                        ),
                        html.Section(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.P(
                                                    "01 / THE BIG PICTURE",
                                                    className="eyebrow",
                                                ),
                                                html.H2("Anatomy of the unknown"),
                                            ]
                                        ),
                                        html.P(
                                            "Every block, a case. "
                                            "Select one to investigate. ↘",
                                            className="section-hint",
                                        ),
                                    ],
                                    className="section-heading",
                                ),
                                html.Div(
                                    dcc.Graph(
                                        id="season-chart",
                                        figure=build_season_chart(EPISODES),
                                        config={
                                            "displayModeBar": False,
                                            "responsive": True,
                                        },
                                    ),
                                    role="img",
                                    **_CHART_ARIA,
                                ),
                                html.P(
                                    [
                                        "Blocks that ",
                                        html.Span("glow", className="chart-note-glow"),
                                        " mark episodes whose opening-title tagline "
                                        "was changed from the usual — ",
                                        dcc.Link("see them all", href="/taglines"),
                                        ".",
                                    ],
                                    className="chart-note",
                                ),
                                build_season_summary_table(EPISODES),
                            ],
                            className="chart-section",
                        ),
                        html.Section(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.P(
                                                    "02 / CASE INDEX", className="eyebrow"
                                                ),
                                                html.H2("Open a file"),
                                            ]
                                        ),
                                        html.P(
                                            "Select an episode to read its dossier.",
                                            className="section-hint",
                                        ),
                                    ],
                                    className="section-heading index-heading",
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Button(
                                                    "‹",
                                                    id="season-prev",
                                                    className="pager-button",
                                                    title="Previous season",
                                                ),
                                                html.Span(
                                                    id="pager-label",
                                                    className="pager-label",
                                                ),
                                                html.Button(
                                                    "›",
                                                    id="season-next",
                                                    className="pager-button",
                                                    title="Next season",
                                                ),
                                            ],
                                            className="season-pager",
                                        ),
                                        html.Label(
                                            "Search episode titles",
                                            htmlFor="search-input",
                                            className="sr-only",
                                        ),
                                        dcc.Input(
                                            id="search-input",
                                            type="text",
                                            placeholder="Search episode titles…",
                                            debounce=True,
                                            className="search-input",
                                        ),
                                        dcc.Checklist(
                                            id="contested-toggle",
                                            options=[
                                                {
                                                    "label": " Contested only",
                                                    "value": "contested",
                                                }
                                            ],
                                            value=[],
                                            className="contested-toggle",
                                        ),
                                        dcc.Checklist(
                                            id="tagline-toggle",
                                            options=[
                                                {
                                                    "label": " Variant taglines only",
                                                    "value": "tagline",
                                                }
                                            ],
                                            value=[],
                                            className="tagline-toggle",
                                        ),
                                        html.Div(id="filter-chip"),
                                    ],
                                    className="controls-row",
                                ),
                                html.Div(id="category-tabs", className="category-tabs"),
                                html.Div(
                                    [
                                        html.P(
                                            id="result-count", className="result-count"
                                        ),
                                        build_episode_table(EPISODES),
                                        html.Div(
                                            id="empty-results", className="empty-results"
                                        ),
                                    ],
                                    className="table-wrap",
                                ),
                                html.Div(
                                    build_detail_panel(EPISODES.iloc[0].to_dict()),
                                    id="detail-panel-container",
                                    className="detail-below",
                                ),
                            ],
                            className="explorer",
                            id="case-index",
                        ),
                    ],
                    id="explore-view",
                ),
                build_taglines_view(EPISODES),
                build_provenance_view(EPISODES),
                build_about(),
            ]
        ),
        footer,
    ],
    className="app-shell",
)


@app.callback(
    Output("nav-explore", "className"),
    Output("nav-taglines", "className"),
    Output("nav-provenance", "className"),
    Output("nav-about", "className"),
    Input("url", "pathname"),
)
def sync_navigation(pathname: str | None):
    route = (pathname or "/").rstrip("/")
    # index 0 is Explore ("/"); the rest map to their route in order.
    routes = ["", "/taglines", "/provenance", "/about"]
    active = routes.index(route) if route in routes else 0
    return tuple(
        "nav-link is-active" if i == active else "nav-link" for i in range(len(routes))
    )


@app.callback(
    Output("category-tabs", "children"),
    Output("result-count", "children"),
    Output("empty-results", "children"),
    Output("episode-table", "style_data_conditional"),
    Input("url", "pathname"),
    Input("url", "search"),
)
def sync_index(pathname: str | None, search: str | None):
    params = parse_qs((search or "").lstrip("?"))
    active = params.get("category", [""])[0]
    tabs = []
    for key, label in (
        ("", "All cases"),
        ("mythology", "Mythology"),
        ("monster-of-the-week", "Monster-of-the-Week"),
        ("standalone", "Standalone"),
    ):
        target = {k: v for k, v in params.items() if k not in ("category", "selected")}
        if key:
            target["category"] = [key]
        query = urlencode(target, doseq=True)
        href = f"/season/{_current_season(pathname)}" + (f"?{query}" if query else "")
        tabs.append(
            dcc.Link(
                label,
                href=href,
                className=("category-tab is-active" if active == key else "category-tab"),
            )
        )
    rows = _table_data(_filter_episodes(pathname, search))
    selected = _selected_record(search, rows)
    styles = list(_STYLE_DATA_CONDITIONAL)
    if selected and any(row["id"] == selected["id"] for row in rows):
        styles.append(
            {
                "if": {"filter_query": '{id} = "' + selected["id"] + '"'},
                "backgroundColor": "#252e24",
                "color": "#e4efcc",
            }
        )
    empty = (
        []
        if rows
        else [
            html.Span("∅", className="empty-symbol"),
            html.H3("No cases match these clues."),
            html.P("Try another title or clear the filters for this season."),
            dcc.Link("Show all cases →", href=f"/season/{_current_season(pathname)}"),
        ]
    )
    count = f"{len(rows):02d} case{'s' if len(rows) != 1 else ''} in view"
    return tabs, count, empty, styles


@app.callback(
    Output("episode-table", "data"),
    Output("filter-chip", "children"),
    Output("detail-panel-container", "children"),
    Output("pager-label", "children"),
    Output("season-prev", "disabled"),
    Output("season-next", "disabled"),
    Output("explore-view", "style"),
    Output("about-section", "style"),
    Output("taglines-section", "style"),
    Output("provenance-section", "style"),
    Input("url", "pathname"),
    Input("url", "search"),
)
def sync_view(pathname: str | None, search: str | None):
    route = (pathname or "/").rstrip("/")
    on_about = route == "/about"
    on_taglines = route == "/taglines"
    on_provenance = route == "/provenance"
    season = _current_season(pathname)
    filtered = _filter_episodes(pathname, search)
    data = _table_data(filtered)
    hidden = {"display": "none"}
    return (
        data,
        _filter_chip(pathname, search),
        build_detail_panel(_selected_record(search, data)),
        _season_label(season),
        season == SEASONS[0],
        season == SEASONS[-1],
        hidden if (on_about or on_taglines or on_provenance) else {},
        {} if on_about else hidden,
        {} if on_taglines else hidden,
        {} if on_provenance else hidden,
    )


@app.callback(
    Output("url", "pathname"),
    Output("url", "search"),
    Input("season-chart", "clickData"),
    Input("episode-table", "active_cell"),
    Input("contested-toggle", "value"),
    Input("tagline-toggle", "value"),
    Input("season-prev", "n_clicks"),
    Input("season-next", "n_clicks"),
    Input("search-input", "value"),
    State("episode-table", "data"),
    State("url", "pathname"),
    State("url", "search"),
    prevent_initial_call=True,
)
def write_url(
    click_data,
    active_cell,
    toggle_value,
    tagline_value,
    prev_clicks,
    next_clicks,
    search_value,
    table_rows,
    pathname,
    search,
):
    trigger = callback_context.triggered_id
    params = parse_qs((search or "").lstrip("?"))
    season = _current_season(pathname)

    if trigger == "season-chart" and click_data:
        custom = (click_data["points"][0].get("customdata")) or {}
        if custom.get("id"):
            # Clicking an episode block jumps to its season page, selected.
            params = {"selected": [custom["id"]]}
            if toggle_value:
                params["contested"] = ["1"]
            if tagline_value:
                params["tagline"] = ["variant"]
            return (
                f"/season/{int(custom['season'])}",
                f"?{urlencode(params, doseq=True)}",
            )

    if trigger == "episode-table" and active_cell and table_rows:
        # Dash supplies a stable row_id even when native sorting changes positions.
        row_id = active_cell.get("row_id")
        if row_id and any(row["id"] == row_id for row in table_rows):
            params["selected"] = [row_id]
            return pathname or "/", f"?{urlencode(params, doseq=True)}"
        row_index = active_cell.get("row")
        if row_index is not None and row_index < len(table_rows):
            params["selected"] = [table_rows[row_index]["id"]]
            return pathname or "/", f"?{urlencode(params, doseq=True)}"

    if trigger in ("season-prev", "season-next"):
        step = -1 if trigger == "season-prev" else 1
        index = SEASONS.index(season) + step
        if 0 <= index < len(SEASONS):
            season = SEASONS[index]
        params.pop("selected", None)  # a new page starts unselected
        return f"/season/{season}", f"?{urlencode(params, doseq=True)}"

    if trigger == "contested-toggle":
        if toggle_value:
            params["contested"] = ["1"]
        else:
            params.pop("contested", None)
        return pathname or "/", f"?{urlencode(params, doseq=True)}"

    if trigger == "tagline-toggle":
        if tagline_value:
            params["tagline"] = ["variant"]
        else:
            params.pop("tagline", None)
        return pathname or "/", f"?{urlencode(params, doseq=True)}"

    if trigger == "search-input":
        if search_value:
            params["text"] = [search_value]
        else:
            params.pop("text", None)
        params.pop("selected", None)
        return pathname or "/", f"?{urlencode(params, doseq=True)}"

    return pathname or "/", search or ""


# --- Server-rendered, crawlable content pages (Group R.3, SEO) ---------------
# Plain Flask routes on the Dash server at paths that do not collide with the
# app's client-side routes (/, /season/<n>, /taglines, /provenance, /about).
# These are what crawlers and no-JS visitors get: episode text in the raw HTML.


@server.route("/episode/<record_id>")
def ssr_episode(record_id: str):
    match = EPISODES[EPISODES["id"] == record_id]
    if match.empty:
        abort(404)
    return render_episode(match.iloc[0].to_dict())


@server.route("/seasons/<int:season>")
def ssr_season(season: int):
    rows = EPISODES[EPISODES["season"] == season].sort_values("air_date")
    if rows.empty:
        abort(404)
    return render_season(season, rows.to_dict("records"))


@server.route("/overview")
def ssr_overview():
    return render_index(EPISODES)


@server.route("/provenance-text")
def ssr_provenance():
    return render_provenance(EPISODES)


@server.route("/sitemap.xml")
def ssr_sitemap():
    return Response(render_sitemap(EPISODES), mimetype="application/xml")


@server.route("/robots.txt")
def ssr_robots():
    return Response(robots_txt(), mimetype="text/plain")


if __name__ == "__main__":
    app.run(debug=True)
