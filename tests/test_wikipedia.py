"""Tests for the Wikipedia wikitext parser (TASKS B-06, B-07, B-08).

All expectations here were counted against the *recorded* fixtures — real
wikitext, not synthetic examples. The landmines these tests pin down
(PRD §8.1):

- Regex-based extraction truncates rows at the first nested `}}` — the
  brace-balanced extractor must survive `{{Start date|...}}`,
  `{{StoryTeleplay|...}}`, and `{{cite episode |...}}` inside rows.
- The mythology dagger is `{{Double-dagger}}` in season 3 but
  `{{double dagger}}` in the revival — detection is case-insensitive on the
  `RTitle` param only (each page also has a legend line that must NOT count).
"""

from __future__ import annotations

import pytest

from build.wikitext import (
    extract_episode_rows,
    is_mythology_flagged,
    parse_wikilinks,
    split_multi_value,
)

# Counted by hand against the recorded fixtures.
EXPECTED_ROWS = {3: 24, 10: 6, 11: 10}
EXPECTED_FLAGGED = {3: 7, 10: 2, 11: 3}


@pytest.mark.parametrize("season", [3, 10, 11])
def test_balanced_extractor_finds_every_episode_row(
    sample_wiki_season_wikitext: dict[int, str], season: int
) -> None:
    rows = extract_episode_rows(sample_wiki_season_wikitext[season])

    assert len(rows) == EXPECTED_ROWS[season]


def test_balanced_extractor_finds_all_16_revival_rows(
    sample_wiki_season_wikitext: dict[int, str],
) -> None:
    """The combined S10+S11 count a regex parser silently drops to zero."""
    revival = extract_episode_rows(
        sample_wiki_season_wikitext[10]
    ) + extract_episode_rows(sample_wiki_season_wikitext[11])

    assert len(revival) == 16


def test_rows_parse_params_despite_nested_templates(
    sample_wiki_season_wikitext: dict[int, str],
) -> None:
    first = extract_episode_rows(sample_wiki_season_wikitext[3])[0]

    assert first["EpisodeNumber"] == "50"
    assert first["EpisodeNumber2"] == "1"
    assert first["ProdCode"] == "3X01"
    # The pipe inside the wikilink must not have split the param.
    assert "The Blessing Way" in first["Title"]


@pytest.mark.parametrize("season", [3, 10, 11])
def test_dagger_detection_is_case_insensitive_on_rtitle(
    sample_wiki_season_wikitext: dict[int, str], season: int
) -> None:
    rows = extract_episode_rows(sample_wiki_season_wikitext[season])

    flagged = [row for row in rows if is_mythology_flagged(row)]

    assert len(flagged) == EXPECTED_FLAGGED[season]


def test_legend_line_never_counts_as_a_flagged_row(
    sample_wiki_season_wikitext: dict[int, str],
) -> None:
    """Every season page explains the dagger in prose; only RTitle counts.

    Season 3's page has 7 daggered rows plus a prose legend line
    ("Episodes marked with a double dagger…") that must not be counted.
    """
    text = sample_wiki_season_wikitext[3]
    # Sanity-check the raw material: the legend line is really there.
    assert "Episodes marked with a double dagger" in text

    rows = extract_episode_rows(text)
    assert sum(1 for row in rows if is_mythology_flagged(row)) == 7


def test_dagger_detection_handles_the_literal_character() -> None:
    """Season 1 flags mythology with a literal ``‡`` (U+2021), not the
    template — found live: 5 season-1 episodes, the difference between
    counting 65 and the expected 70.
    """
    assert is_mythology_flagged({"RTitle": "‡"})
    assert is_mythology_flagged({"RTitle": " ‡ "})


def test_footnote_rtitle_is_not_a_dagger() -> None:
    """Rm9sbG93ZXJz's RTitle is a Base64 footnote, not a mythology flag."""
    assert not is_mythology_flagged(
        {"RTitle": '{{#tag:ref|This is [[Base64]] for "Followers".}}'}
    )


def test_strip_refs_removes_citation_markup() -> None:
    """Fox volume articles append ``<ref>`` citations to production codes."""
    from build.wikitext import strip_refs

    assert strip_refs('3X09<ref name="S3date">{{cite AV media notes}}</ref>') == "3X09"
    assert strip_refs('3X10<ref name="S3date"/>') == "3X10"
    assert strip_refs("1X79") == "1X79"


def test_split_multi_value_on_hr_variants() -> None:
    # Mid-run seasons join multi-director rows with <hr>; the recorded
    # fixture seasons happen not to, so this documents the contract.
    assert split_multi_value("[[Kim Manners]]<hr>[[Rob Bowman]]") == [
        "[[Kim Manners]]",
        "[[Rob Bowman]]",
    ]
    assert split_multi_value("A<hr/>B<hr />C") == ["A", "B", "C"]
    assert split_multi_value("just one") == ["just one"]
    assert split_multi_value("") == []


def test_parse_wikilinks_extracts_display_names() -> None:
    assert parse_wikilinks("[[The Blessing Way (The X-Files)|The Blessing Way]]") == [
        "The Blessing Way"
    ]
    assert parse_wikilinks("[[R. W. Goodwin]]") == ["R. W. Goodwin"]
    assert parse_wikilinks("[[Glen Morgan]] & [[James Wong (producer)|James Wong]]") == [
        "Glen Morgan",
        "James Wong",
    ]
    # Revival pages drop the links entirely for some writers.
    assert parse_wikilinks("Chris Carter") == ["Chris Carter"]
    assert parse_wikilinks("") == []
