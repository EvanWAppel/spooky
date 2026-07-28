"""Tests for the merge core (TASKS B-10, B-11, E-03).

The two-parter policy (PRD §8.1 step 07): TVmaze splits "The Truth" into
two rows (218); Wikipedia merges it into one ``<hr>``-joined row (217).
The merge takes TVmaze's shape and duplicates Wikipedia's values across
both rows.
"""

from __future__ import annotations

from build.merge import expand_wiki_rows, join_wikidata, wiki_link_target

# The real season-9 row, verbatim from the recorded page (revid-tracked in
# data/raw/wiki_seasons/wiki_s09.json).
TRUTH_ROW = {
    "EpisodeNumber": "201<hr>202",
    "EpisodeNumber2": "19<hr>20",
    "Title": "[[The Truth (The X-Files)|The Truth]]",
    "RTitle": "{{Double-dagger}}",
    "ProdCode": "9ABX19<hr>9ABX20",
    "DirectedBy": "[[Kim Manners]]",
}

ORDINARY_ROW = {
    "EpisodeNumber": "1",
    "EpisodeNumber2": "1",
    "Title": "[[Pilot (The X-Files)|Pilot]]",
    "ProdCode": "1X79",
}


def test_truth_expands_to_two_rows_with_wikipedia_values_duplicated() -> None:
    keyed = expand_wiki_rows({9: [TRUTH_ROW]})

    assert set(keyed) == {(9, 19), (9, 20)}
    assert keyed[(9, 19)]["ProdCode"] == "9ABX19"
    assert keyed[(9, 20)]["ProdCode"] == "9ABX20"
    # Everything Wikipedia merged is duplicated across both rows.
    for key in ((9, 19), (9, 20)):
        assert keyed[key]["Title"] == TRUTH_ROW["Title"]
        assert keyed[key]["RTitle"] == TRUTH_ROW["RTitle"]
        assert keyed[key]["DirectedBy"] == "[[Kim Manners]]"


def test_ordinary_rows_key_on_season_and_number() -> None:
    keyed = expand_wiki_rows({1: [ORDINARY_ROW]})

    assert set(keyed) == {(1, 1)}
    assert keyed[(1, 1)]["ProdCode"] == "1X79"


def test_wiki_link_target_extracts_article_title() -> None:
    assert (
        wiki_link_target("[[The Sixth Extinction II: Amor Fati|Amor Fati]]")
        == "The Sixth Extinction II: Amor Fati"
    )
    assert wiki_link_target("[[Tooms]]") == "Tooms"
    assert wiki_link_target("no link here") is None


def test_amor_fati_joins_wikidata_without_a_miss() -> None:
    """B-11: TVmaze calls it "The Sixth Extinction: Amor Fati"; Wikipedia
    "The Sixth Extinction II: Amor Fati". The join goes wiki-row link target
    -> Wikidata enwiki_title — both Wikipedia-side — so the TVmaze spelling
    never enters the join at all.
    """
    amor_fati = "The Sixth Extinction II: Amor Fati"
    wiki_row = {
        "EpisodeNumber2": "2",
        "Title": f"[[{amor_fati}|{amor_fati}]]",
    }
    wikidata_rows = [
        {
            "qid": "Q116441",
            "label": "The Sixth Extinction II: Amor Fati",
            "imdb_id": "tt0751212",
            "enwiki_title": "The Sixth Extinction II: Amor Fati",
        }
    ]

    matched = join_wikidata(
        wiki_row,
        tvmaze_name="The Sixth Extinction: Amor Fati",
        rows=wikidata_rows,
    )

    assert matched is not None
    assert matched["qid"] == "Q116441"


def test_join_falls_back_to_tvmaze_name_when_no_wiki_row() -> None:
    matched = join_wikidata(
        None,
        tvmaze_name="Pilot",
        rows=[{"qid": "Q1", "label": "Pilot", "imdb_id": "tt1", "enwiki_title": None}],
    )

    assert matched is not None
    assert matched["qid"] == "Q1"


def test_fox_join_is_title_only_and_ignores_production_codes() -> None:
    """The Mythology volume articles number production codes on a different
    convention than the season pages (their "Deep Throat 1X02" is the season
    page's Squeeze) — a code join labels each entry's neighbor. Title only.
    """
    from build.merge import _fox_label, _norm_title

    fox_titles = {_norm_title("Deep Throat"), _norm_title("The Erlenmeyer Flask")}

    assert _fox_label(1, "Deep Throat", fox_titles) == "mythology"
    assert _fox_label(1, "The Erlenmeyer Flask", fox_titles) == "mythology"
    assert _fox_label(1, "Squeeze", fox_titles) == "not-listed"
    # The sets predate the revival: seasons 10-11 abstain.
    assert _fox_label(10, "My Struggle", fox_titles) is None


def test_join_maps_tvmaze_part_suffixes_to_wikidata_roman_labels() -> None:
    """TVmaze names two-parters "Redux (1)"/"Redux (2)"; Wikidata labels the
    same items "Redux"/"Redux II", with no enwiki sitelink (the parts share
    one article). Found live: 6 such misses across the corpus.
    """
    rows = [
        {
            "qid": "Q50279722",
            "label": "Redux",
            "imdb_id": "tt0751187",
            "enwiki_title": None,
        },
        {
            "qid": "Q21653833",
            "label": "Redux II",
            "imdb_id": "tt0751188",
            "enwiki_title": None,
        },
    ]

    part1 = join_wikidata(None, tvmaze_name="Redux (1)", rows=rows)
    part2 = join_wikidata(None, tvmaze_name="Redux (2)", rows=rows)

    assert part1 is not None and part1["qid"] == "Q50279722"
    assert part2 is not None and part2["qid"] == "Q21653833"
