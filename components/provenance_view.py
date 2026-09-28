"""The /provenance view — the data-engineering dashboard (TASKS R-06).

Surfaces what the dataset already stores: how the three classification sources
disagree, which episodes are contested and how each source voted, and every
field's source + licence. All numbers are re-derived from the records at render
time (CLAUDE.md). Plain site text and original markup only — no imagery (C2).
"""

from __future__ import annotations

import pandas as pd
from dash import html

from spooky.provenance import (
    contested_breakdown,
    field_provenance,
    source_coverage,
)


def build_provenance_view(df: pd.DataFrame) -> html.Section:
    total = len(df)
    contested = contested_breakdown(df)
    return html.Section(
        [
            html.P("03 / WHERE THE DATA COMES FROM", className="eyebrow"),
            html.H2("Provenance & the disagreement"),
            html.P(
                [
                    "There is no settled answer to “is this episode mythology?” "
                    "Three sources vote; a source that does not cover a record "
                    "abstains rather than counting as a “no”. Of ",
                    html.Strong(f"{total} records"),
                    ", ",
                    html.Strong(f"{len(contested)}"),
                    " are contested — the sources disagree, or fewer than three "
                    "cover them. Every figure on this page is recomputed from the "
                    "dataset, never hard-coded.",
                ]
            ),
            _coverage_table(df),
            _contested_table(contested),
            _field_table(df),
            html.P(
                [
                    "Field-level provenance carries a Wikipedia revision id "
                    "wherever the value came from a specific revision, so any "
                    "claim traces back to the exact source that made it. Full "
                    "field dictionary in ",
                    html.Code("data/README.md"),
                    ".",
                ],
                className="provenance-footnote",
            ),
        ],
        id="provenance-section",
        className="provenance-section",
    )


def _coverage_table(df: pd.DataFrame) -> html.Div:
    rows = [
        html.Tr(
            [
                html.Td(row["label"]),
                html.Td(str(row["covers"]), className="num"),
                html.Td(str(row["abstains"]), className="num"),
                html.Td(str(row["mythology"]), className="num"),
            ]
        )
        for row in source_coverage(df)
    ]
    return html.Div(
        [
            html.H3("What each source covers"),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Source"),
                                html.Th("Covers", className="num"),
                                html.Th("Abstains", className="num"),
                                html.Th("Calls mythology", className="num"),
                            ]
                        )
                    ),
                    html.Tbody(rows),
                ],
                className="provenance-table coverage-table",
            ),
        ]
    )


def _contested_table(contested: list[dict]) -> html.Div:
    rows = [
        html.Tr(
            [
                html.Td(f"{row['season_episode']} · {row['title']}"),
                html.Td(_verdict(row["label_fox_dvd"])),
                html.Td(_verdict(row["label_wikipedia"])),
                html.Td(_verdict(row["label_dom111"])),
                html.Td(_verdict(row["label_derived"]), className="derived"),
                html.Td(row["label_rationale"], className="rationale"),
            ]
        )
        for row in contested
    ]
    return html.Div(
        [
            html.H3(f"The {len(contested)} contested records"),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Episode"),
                                html.Th("Fox DVDs"),
                                html.Th("Wikipedia"),
                                html.Th("dom111"),
                                html.Th("Derived"),
                                html.Th("Why"),
                            ]
                        )
                    ),
                    html.Tbody(rows),
                ],
                className="provenance-table contested-table",
            ),
        ]
    )


def _field_table(df: pd.DataFrame) -> html.Div:
    rows = [
        html.Tr(
            [
                html.Td(html.Code(row["field"])),
                html.Td(", ".join(row["sources"]) or "—"),
                html.Td(", ".join(row["licenses"]) or "—"),
                html.Td("yes" if row["has_revid"] else "—", className="num"),
            ]
        )
        for row in field_provenance(df)
    ]
    return html.Div(
        [
            html.H3("Every field's source & licence"),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Field"),
                                html.Th("Source"),
                                html.Th("Licence"),
                                html.Th("Revision-pinned", className="num"),
                            ]
                        )
                    ),
                    html.Tbody(rows),
                ],
                className="provenance-table field-table",
            ),
        ]
    )


def _verdict(value: str | None) -> str:
    """A source's verdict for the split table; abstention reads as 'no data'."""
    return "no data" if value is None else value
