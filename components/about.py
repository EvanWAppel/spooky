from __future__ import annotations

from dash import html


def build_about() -> html.Section:
    """The /about view: why three labels, and why the sources disagree (H-08)."""
    return html.Section(
        [
            html.H2("Why three labels — and why the sources disagree"),
            html.P(
                "Fans divide The X-Files into “mythology” — the "
                "long-running conspiracy arc — and “monster-of-the-week.” "
                "It sounds like a settled question. It is not: no two "
                "authorities agree on where the line sits, and roughly one "
                "episode in ten is claimed differently by different sources."
            ),
            html.H3("The three sources"),
            html.Ul(
                [
                    html.Li(
                        [
                            html.Strong("The Fox “Mythology” DVD sets"),
                            " — four box sets Fox released in 2005, curating "
                            "the conspiracy arc. The closest thing to an "
                            "official canon, but they predate the revival by "
                            "a decade and omit episodes fans consider "
                            "essential (famously “Musings of a Cigarette "
                            "Smoking Man”).",
                        ]
                    ),
                    html.Li(
                        [
                            html.Strong("Wikipedia"),
                            " — the episode lists flag mythology entries "
                            "with a double dagger (‡). Broad and "
                            "maintained, but the revival flags are editorial "
                            "judgment rather than sourced.",
                        ]
                    ),
                    html.Li(
                        [
                            html.Strong("dom111/xfiles-episode-picker"),
                            " — an open-source fan project labeling all 218 "
                            "episodes as mythology or monster-of-the-week. "
                            "Complete and consistent; one person's judgment.",
                        ]
                    ),
                ]
            ),
            html.H3("How the derived label works"),
            html.P(
                "Each record stores all three source labels. A source that "
                "does not cover a record — the DVD sets stop before the "
                "revival; no episode source covers the films — abstains "
                "rather than voting no. A strict majority of the votes that "
                "exist decides mythology; otherwise the episode is "
                "monster-of-the-week if it features a non-recurring "
                "paranormal antagonist, and standalone if it does not."
            ),
            html.P(
                [
                    "Any disagreement, and any record with fewer than three "
                    "votes, is marked ",
                    html.Span("Contested", className="contested-badge"),
                    " — with the per-source breakdown shown on the episode "
                    "panel. The disagreement is not noise to be smoothed "
                    "over; it is the most interesting thing in the data.",
                ]
            ),
            html.H3("Data and licensing"),
            html.P(
                "Episode metadata and ratings come from TVmaze, structure "
                "and flags from Wikipedia, identifiers from Wikidata — each "
                "field on each record carries its source, license, and where "
                "applicable the exact article revision. The derived dataset "
                "is published under CC BY-SA 4.0. No synopses, no imagery, "
                "no IMDb ratings — by design; the footer has the details."
            ),
        ],
        id="about-section",
        className="about-section",
    )
