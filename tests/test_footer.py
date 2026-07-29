"""The footer attribution must be verbatim (TASKS J-06; PRD §11.2).

CC BY-SA attribution is a licence condition, not a stylistic choice — so
the rendered text is compared against the canonical wording character for
character, with the required links present.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import app as app_module

ATTRIBUTION = (
    "Episode metadata and ratings from TVmaze, licensed CC BY-SA 4.0. "
    "Additional episode data derived from Wikipedia, licensed CC BY-SA 4.0; "
    "modified. Identifier data from Wikidata (CC0). "
    "Mythology/monster-of-the-week labels adapted from "
    "dom111/xfiles-episode-picker (MIT). "
    "The derived dataset published here is licensed CC BY-SA 4.0."
)
DISCLAIMER = (
    "This is an unofficial fan project. It is not affiliated with, endorsed "
    "by, or approved by 20th Television, The Walt Disney Company, or Ten "
    "Thirteen Productions. The X-Files and all related marks are the property "
    "of their respective owners. Contact: appelew@gmail.com"
)
TMDB_CLAUSE = (
    "This website uses TMDB and the TMDB APIs but is not endorsed, certified, "
    "or otherwise approved by TMDB."
)
REQUIRED_LINKS = (
    "https://www.tvmaze.com",
    "https://en.wikipedia.org/wiki/List_of_The_X-Files_episodes",
    "https://www.wikidata.org",
    "https://github.com/dom111/xfiles-episode-picker",
    "https://creativecommons.org/licenses/by-sa/4.0/",
)


def _visible_text(component: Any) -> str:
    """Flatten to the text a reader actually sees — no href values.

    The shared `render_text` fixture deliberately includes hrefs so link
    tests can assert on them; that makes it useless for comparing prose.
    """
    if component is None:
        return ""
    if isinstance(component, str):
        return component
    if isinstance(component, list | tuple):
        return " ".join(_visible_text(child) for child in component)
    children = getattr(component, "children", None)
    if children is not None:
        return _visible_text(children)
    return str(component)


def _normalized(text: str) -> str:
    """Collapse whitespace the way a browser renders inline nodes.

    Flattening joins a component's children with spaces, so an inline link
    followed by punctuation — `<a>TVmaze</a>, licensed` — comes back as
    "TVmaze , licensed". The DOM has no such space; drop it before
    comparing, or the verbatim check fails on an artifact of the harness.
    """
    collapsed = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s+([,.;:])", r"\1", collapsed)


def test_footer_carries_the_verbatim_attribution() -> None:
    rendered = _normalized(_visible_text(app_module.footer))

    assert ATTRIBUTION in rendered
    assert DISCLAIMER in rendered
    assert TMDB_CLAUSE in rendered


def test_footer_links_to_every_required_source(
    render_text: Callable[[Any], str],
) -> None:
    rendered = render_text(app_module.footer)

    for url in REQUIRED_LINKS:
        assert url in rendered, f"footer is missing the {url} link"


def test_footer_never_claims_no_infringement_intended() -> None:
    """CLAUDE.md: the phrase has no legal effect and must never appear."""
    rendered = _visible_text(app_module.footer).lower()

    assert "no copyright infringement intended" not in rendered


def test_noscript_block_carries_the_same_attribution() -> None:
    """Crawlers and no-JS visitors must still get the licence notice."""
    index = _normalized(app_module.app.index_string)

    assert "unofficial fan project" in index
    assert "CC BY-SA 4.0" in index
    assert "TMDB" in index
