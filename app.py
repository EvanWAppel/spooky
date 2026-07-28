from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode

from dash import Dash, Input, Output, State, callback_context, dcc, html

from components.about import build_about
from components.chart import build_season_chart, build_season_summary_table
from components.films import build_films_card
from components.panel import build_detail_panel
from components.table import build_episode_table
from spooky.loader import load_episodes
from spooky.logging_config import setup_logging

setup_logging()

EPISODES = load_episodes(Path(__file__).resolve().parent / "data" / "episodes")

# Wildcard aria-* props are legal on Dash HTML components at runtime but
# absent from the generated stubs — routed through a typed-as-Any dict so
# ty stays clean without an ignore comment.
_CHART_ARIA: dict[str, Any] = {
    "aria-label": (
        "Stacked bar chart of episodes per season, split into mythology, "
        "monster-of-the-week, and standalone. A data table with the same "
        "numbers follows."
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


def _filter_episodes(pathname: str | None, search: str | None):
    df = EPISODES.copy()
    if pathname and pathname.startswith("/season/"):
        season_text = pathname.removeprefix("/season/").split("/", maxsplit=1)[0]
        if season_text.isdigit():
            df = df[df["season"] == int(season_text)]

    params = parse_qs((search or "").lstrip("?"))
    category = params.get("category", [None])[0]
    if category:
        df = df[df["label_derived"] == category]

    text = params.get("text", [None])[0]
    if text:
        df = df[df["title"].str.contains(text, case=False, na=False)]

    if params.get("contested", [None])[0] == "1":
        df = df[df["label_contested"]]

    return df


def _table_data(df):
    table = build_episode_table(df)
    return table.to_plotly_json()["props"]["data"]


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
    }.get(category or "", "All categories")


def _filter_chip(pathname: str | None, search: str | None) -> html.Div:
    params = parse_qs((search or "").lstrip("?"))
    season = "All seasons"
    if pathname and pathname.startswith("/season/"):
        season_value = pathname.removeprefix("/season/").split("/", maxsplit=1)[0]
        if season_value.isdigit():
            season = f"Season {season_value}"
    category = _category_label(params.get("category", [None])[0])
    parts = [season, category]
    if params.get("contested", [None])[0] == "1":
        parts.append("Contested only")
    return html.Div(
        [
            html.Span(" · ".join(parts)),
            dcc.Link("Clear", href="/", className="clear-filter"),
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
        # would filter by category across all seasons. See tests/test_app_routing.py.
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
                                build_season_summary_table(EPISODES),
                                html.Div(
                                    [
                                        html.Div(id="filter-chip"),
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
                                    ],
                                    className="filter-row",
                                ),
                            ],
                            className="chart-section",
                        ),
                        html.Section(
                            [
                                html.Div(
                                    build_episode_table(EPISODES),
                                    className="table-wrap",
                                ),
                                html.Div(
                                    build_detail_panel(EPISODES.iloc[0].to_dict()),
                                    id="detail-panel-container",
                                ),
                            ],
                            className="explorer",
                        ),
                        build_films_card(EPISODES),
                    ],
                    id="explore-view",
                ),
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
    Output("explore-view", "style"),
    Output("about-section", "style"),
    Input("url", "pathname"),
    Input("url", "search"),
)
def sync_view(pathname: str | None, search: str | None):
    on_about = (pathname or "/").rstrip("/") == "/about"
    filtered = _filter_episodes(pathname, search)
    data = _table_data(filtered)
    return (
        _table_data(filtered),
        _filter_chip(pathname, search),
        build_detail_panel(_selected_record(search, data)),
        {"display": "none"} if on_about else {},
        {} if on_about else {"display": "none"},
    )


@app.callback(
    Output("url", "pathname"),
    Output("url", "search"),
    Input("season-chart", "clickData"),
    Input("episode-table", "active_cell"),
    Input("contested-toggle", "value"),
    State("episode-table", "data"),
    State("url", "pathname"),
    State("url", "search"),
    prevent_initial_call=True,
)
def write_url(click_data, active_cell, toggle_value, table_rows, pathname, search):
    trigger = callback_context.triggered_id
    params = parse_qs((search or "").lstrip("?"))

    if trigger == "season-chart" and click_data:
        point = click_data["points"][0]
        custom = point.get("customdata") or {}
        season = custom.get("season") or point.get("x")
        category = custom.get("category")
        params = {"category": [category]} if category else {}
        if toggle_value:
            params["contested"] = ["1"]
        return f"/season/{int(season)}", f"?{urlencode(params, doseq=True)}"

    if trigger == "episode-table" and active_cell and table_rows:
        row_index = active_cell.get("row")
        if row_index is not None and row_index < len(table_rows):
            params["selected"] = [table_rows[row_index]["id"]]
            return pathname or "/", f"?{urlencode(params, doseq=True)}"

    if trigger == "contested-toggle":
        if toggle_value:
            params["contested"] = ["1"]
        else:
            params.pop("contested", None)
        return pathname or "/", f"?{urlencode(params, doseq=True)}"

    return pathname or "/", search or ""


if __name__ == "__main__":
    app.run(debug=True)
