from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode

import pandas as pd
from dash import Dash, Input, Output, State, callback_context, dcc, html

from components.about import build_about
from components.chart import build_season_chart, build_season_summary_table
from components.panel import build_detail_panel
from components.table import build_episode_table
from components.taglines_view import build_taglines_view
from spooky.loader import load_episodes
from spooky.logging_config import setup_logging

setup_logging()

EPISODES = load_episodes(Path(__file__).resolve().parent / "data" / "episodes")

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
    film_ids = [film_id for film_id, page in FILM_PAGE.items() if page == season]
    df = EPISODES[
        (EPISODES["season"] == season) | (EPISODES["id"].isin(film_ids))
    ].sort_values("air_date")

    params = parse_qs((search or "").lstrip("?"))
    category = params.get("category", [None])[0]
    if category:
        df = df[df["label_derived"] == category]

    text = params.get("text", [None])[0]
    if text:
        df = df[df["title"].str.contains(text, case=False, na=False)]

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
        parts.append(f"matching “{params['text'][0]}”")
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
        html.Header(
            [
                html.Div(
                    [
                        html.Img(
                            src="/assets/spooky.svg",
                            alt="",
                            className="site-mark",
                            role="presentation",
                        ),
                        html.Div(
                            [
                                html.P(
                                    "The X-Files episode data explorer",
                                    className="eyebrow",
                                ),
                                html.H1("spooky"),
                            ]
                        ),
                    ],
                    className="masthead",
                ),
                html.P(
                    "A tested, source-aware view of how the series balances mythology, "
                    "monster cases, and standalone stories.",
                    className="lede",
                ),
                html.Nav(
                    [
                        dcc.Link("Explore", href="/", className="nav-link"),
                        dcc.Link("Taglines", href="/taglines", className="nav-link"),
                        dcc.Link("About", href="/about", className="nav-link"),
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
                                        dcc.Input(
                                            id="search-input",
                                            type="text",
                                            placeholder="Search titles…",
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
                                html.Div(
                                    build_episode_table(EPISODES),
                                    className="table-wrap",
                                ),
                                html.Div(
                                    build_detail_panel(EPISODES.iloc[0].to_dict()),
                                    id="detail-panel-container",
                                    className="detail-below",
                                ),
                            ],
                            className="explorer",
                        ),
                    ],
                    id="explore-view",
                ),
                build_taglines_view(EPISODES),
                build_about(),
            ]
        ),
        footer,
    ],
    className="app-shell",
)


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
    Input("url", "pathname"),
    Input("url", "search"),
)
def sync_view(pathname: str | None, search: str | None):
    route = (pathname or "/").rstrip("/")
    on_about = route == "/about"
    on_taglines = route == "/taglines"
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
        hidden if (on_about or on_taglines) else {},
        {} if on_about else hidden,
        {} if on_taglines else hidden,
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


if __name__ == "__main__":
    app.run(debug=True)
