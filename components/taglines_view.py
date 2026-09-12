"""The /taglines view — the opening-title tagline catalogue (TASKS T-10).

The community-facing centrepiece: every episode whose opening-credits tagline
was swapped from the usual "The Truth Is Out There", in airing order, each
linking to its episode. Taglines are plain site text — never the show's
title-card styling or imagery (CLAUDE.md C2).
"""

from __future__ import annotations

import pandas as pd
from dash import dcc, html

from spooky.taglines import DEFAULT_TAGLINE, note_of, text_of


def build_taglines_view(df: pd.DataFrame) -> html.Section:
    variants = df[df["tagline_is_variant"]].sort_values("air_date")
    rows = [_row(record) for _, record in variants.iterrows()]
    return html.Section(
        [
            html.H2("The opening-title taglines"),
            html.P(
                [
                    "Every episode's title sequence ends on a card reading ",
                    html.Strong(f"“{DEFAULT_TAGLINE}.”"),
                    " In a handful of episodes it is deliberately swapped for a "
                    "line that speaks to that story — an authorial wink the "
                    "fandom has tracked for decades. Here is every one, in "
                    "airing order.",
                ]
            ),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Episode"),
                                html.Th("Tagline"),
                                html.Th(""),
                            ]
                        )
                    ),
                    html.Tbody(rows),
                ],
                className="taglines-table",
            ),
            html.P(
                [
                    f"There are {len(rows)} of them. Each tagline is recorded "
                    "verbatim from the episode's Wikipedia article (CC BY-SA); "
                    "translations of the non-English lines — the Navajo of "
                    "“Anasazi”, for one — are contested between sources, so we "
                    "show the line as written and leave the gloss to review."
                ],
                className="taglines-footnote",
            ),
        ],
        id="taglines-section",
        className="taglines-section",
    )


def _row(record: pd.Series) -> html.Tr:
    data = record.to_dict()
    season = int(record["season"])
    href = f"/season/{season}?selected={record['id']}"
    note = note_of(data)
    tagline_cell: list = [html.Span(text_of(data), className="tagline-line")]
    if note:
        tagline_cell.append(html.Span(note, className="tagline-note"))
    return html.Tr(
        [
            html.Td(
                dcc.Link(
                    f"{record['season_episode']} · {record['title']}",
                    href=href,
                    className="tagline-episode-link",
                )
            ),
            html.Td(tagline_cell),
            html.Td(
                dcc.Link("View", href=href, className="tagline-view-link"),
                className="tagline-view-cell",
            ),
        ]
    )
