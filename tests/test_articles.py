"""Tests for article section + link extraction (TASKS D-13, D-14).

The fixture is the real "Squeeze (The X-Files)" article wikitext, distilled
from the one-POST Special:Export of 2026-07-27 (revid 1334224906).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from build.articles import episode_links, extract_section, parse_export

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "article_squeeze.txt"


@pytest.fixture(scope="module")
def squeeze() -> str:
    return FIXTURE.read_text()


def test_extract_production_section(squeeze: str) -> None:
    production = extract_section(squeeze, "Production")

    assert production is not None
    assert len(production) > 1000


def test_extract_is_case_insensitive_and_missing_is_none(squeeze: str) -> None:
    assert extract_section(squeeze, "themes") is not None
    assert extract_section(squeeze, "Conspiracy Corner") is None


def test_level_3_headings_do_not_terminate_a_section() -> None:
    wikitext = "== Production ==\nintro\n=== Casting ===\ndetail\n== Reception ==\nend"

    production = extract_section(wikitext, "Production")

    assert production is not None
    assert "Casting" in production
    assert "end" not in production


def test_episode_links_filter_to_known_titles(squeeze: str) -> None:
    known = {"Tooms", "Pilot (The X-Files)", "Squeeze (The X-Files)"}

    links = episode_links(squeeze, known)

    assert "Tooms" in links
    assert "Pilot (The X-Files)" in links
    # Non-episode links never leak through.
    assert all(link in known for link in links)


def test_parse_export_reads_titles_revids_and_text() -> None:
    xml = (
        '<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/">'
        "<page><title>Tooms</title><revision><id>123</id>"
        "<text>Eugene Victor Tooms returns.</text></revision></page>"
        "</mediawiki>"
    )

    articles = parse_export(xml)

    assert articles == {
        "Tooms": {"revid": 123, "wikitext": "Eugene Victor Tooms returns."}
    }


def test_parse_export_raises_on_missing_revision_id() -> None:
    xml = (
        '<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/">'
        "<page><title>Tooms</title><revision>"
        "<text>no id</text></revision></page>"
        "</mediawiki>"
    )

    with pytest.raises(RuntimeError, match="no revision id"):
        parse_export(xml)
