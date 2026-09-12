"""Tagline extraction, derivation, attach, and drift (TASKS T-02/T-04/T-05).

The prose fixtures in ``tests/fixtures/tagline_prose.json`` are real
Production-section snippets recorded from ``data/raw/article_sections.json``
(D-13/D-14 output) — the suite runs entirely offline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from build.taglines import (
    attach_taglines,
    build_tagline,
    extract_variant,
    find_drift,
    load_overrides,
    tagline_provenance,
)
from spooky.taglines import DEFAULT_TAGLINE, is_variant, normalize

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def tagline_prose() -> dict[str, dict]:
    return json.loads((FIXTURES_DIR / "tagline_prose.json").read_text())


# --- normalization / is_variant -------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "The Truth Is Out There",
        "The Truth is Out There",
        "the truth is out there",
        "The Truth is Out There.",
    ],
)
def test_default_variants_are_not_flagged_as_variants(text: str) -> None:
    """Wikipedia's casing of the default is inconsistent; none is a variant."""
    assert is_variant(text) is False
    assert normalize(text) == normalize(DEFAULT_TAGLINE)


@pytest.mark.parametrize("text", ["Apology is Policy", "Trust No One", "amor fati"])
def test_real_lines_are_variants(text: str) -> None:
    assert is_variant(text) is True


def test_blank_is_not_a_variant() -> None:
    assert is_variant("") is False
    assert is_variant(None) is False


# --- prose extraction -----------------------------------------------------------


@pytest.mark.parametrize(
    ("article", "expected"),
    [
        ("The Erlenmeyer Flask", "Trust No One"),
        ("Anasazi (The X-Files)", "Éí 'Aaníígóó 'Áhoot'é"),
        ("731 (The X-Files)", "Apology is Policy"),
        ("Herrenvolk (The X-Files)", "Everything Dies"),
        ("Terma (The X-Files)", "E pur si muove"),
    ],
)
def test_extract_variant_pulls_the_documented_tagline(
    tagline_prose: dict[str, dict], article: str, expected: str
) -> None:
    assert extract_variant(tagline_prose[article]["production"]) == expected


def test_extract_variant_returns_none_for_a_default_episode(
    tagline_prose: dict[str, dict],
) -> None:
    """2Shy documents no tagline change, so it carries the default (None here)."""
    assert extract_variant(tagline_prose["2Shy"]["production"]) is None


def test_extract_variant_returns_none_when_the_line_is_non_adjacent(
    tagline_prose: dict[str, dict],
) -> None:
    """Teliko names the tagline in a sentence apart from the "replaces the usual
    tagline" clause — the scanner cannot lift it, which is exactly why it is a
    MANUAL entry in the seed tool."""
    assert extract_variant(tagline_prose["Teliko"]["production"]) is None


def test_extract_variant_ignores_a_mention_of_only_the_default() -> None:
    prose = 'The usual tagline "The Truth Is Out There" appears after the credits.'
    assert extract_variant(prose) is None


# --- tagline object + provenance ------------------------------------------------


def test_build_tagline_derives_is_variant_and_never_trusts_the_override() -> None:
    overrides = {"s03e10": {"id": "s03e10", "tagline": "Apology is Policy", "revid": 1}}
    variant = build_tagline("s03e10", overrides)
    assert variant["text"] == "Apology is Policy"
    assert variant["is_variant"] is True

    default = build_tagline("s03e15", overrides)
    assert default["text"] == DEFAULT_TAGLINE
    assert default["is_variant"] is False


def test_tagline_provenance_cites_wikipedia_revid_for_variants() -> None:
    overrides = {"s03e10": {"id": "s03e10", "tagline": "Apology is Policy", "revid": 42}}
    variant = tagline_provenance("s03e10", overrides)
    assert variant["source"] == "Wikipedia"
    assert variant["license"] == "CC BY-SA 4.0"
    assert isinstance(variant["revid"], int)

    default = tagline_provenance("s03e15", overrides)
    assert "series default" in default["source"]
    assert default["license"] == "CC BY-SA 4.0"
    assert "revid" not in default


# --- drift ----------------------------------------------------------------------


def test_find_drift_flags_a_documented_change_missing_from_the_override(
    tagline_prose: dict[str, dict],
) -> None:
    sections = {"731 (The X-Files)": tagline_prose["731 (The X-Files)"]}
    id_by_article = {"731 (The X-Files)": "s03e10"}
    # Override omits s03e10 — the prose documents a swap it does not list.
    assert find_drift({}, sections, id_by_article)
    # Override lists it — no drift.
    assert find_drift({"s03e10": {}}, sections, id_by_article) == []


def test_committed_override_has_no_drift() -> None:
    """The shipped taglines.json stays in sync with the article prose.

    ``data/raw`` is a gitignored build input, so it is absent in CI; there the
    drift check is enforced by the ``taglines`` build step instead. This test
    runs wherever the raw prose is present (locally, and in the pipeline).
    """
    sections_path = REPO_ROOT / "data" / "raw" / "article_sections.json"
    if not sections_path.exists():
        pytest.skip("data/raw is gitignored — drift is enforced at build time")
    overrides = load_overrides(REPO_ROOT / "data" / "overrides")
    sections = json.loads(sections_path.read_text())
    id_by_article: dict[str, str] = {}
    for path in (REPO_ROOT / "data" / "episodes").glob("*.json"):
        record = json.loads(path.read_text())
        for key in (record.get("enwiki_title"), record.get("title")):
            if key:
                id_by_article.setdefault(key, record["id"])
    assert find_drift(overrides, sections, id_by_article) == []


# --- attach (in place, preserves loglines, idempotent) --------------------------


def _write(dir_: Path, record: dict) -> None:
    (dir_ / f"{record['id']}.json").write_text(json.dumps(record, indent=1))


def test_attach_taglines_adds_tagline_and_preserves_loglines(tmp_data_dir: Path) -> None:
    episodes = tmp_data_dir / "episodes"
    overrides = tmp_data_dir / "overrides"
    (overrides / "taglines.json").write_text(
        json.dumps([{"id": "s03e10", "tagline": "Apology is Policy", "revid": 7}])
    )
    _write(
        episodes,
        {
            "id": "s03e10",
            "logline_generated": "a precious machine draft",
            "logline": None,
            "review_status": "ai-drafted",
            "provenance": {},
        },
    )
    _write(
        episodes,
        {"id": "s03e15", "logline_generated": "another draft", "provenance": {}},
    )

    total, variants = attach_taglines(episodes, overrides)
    assert (total, variants) == (2, 1)

    variant = json.loads((episodes / "s03e10.json").read_text())
    assert variant["tagline"]["text"] == "Apology is Policy"
    assert variant["tagline"]["is_variant"] is True
    # The logline layer is untouched — the whole reason attach is not the merge.
    assert variant["logline_generated"] == "a precious machine draft"
    assert variant["review_status"] == "ai-drafted"
    assert variant["provenance"]["tagline.text"]["revid"] == 7

    default = json.loads((episodes / "s03e15.json").read_text())
    assert default["tagline"]["text"] == DEFAULT_TAGLINE
    assert default["tagline"]["is_variant"] is False


def test_attach_taglines_is_idempotent(tmp_data_dir: Path) -> None:
    episodes = tmp_data_dir / "episodes"
    overrides = tmp_data_dir / "overrides"
    (overrides / "taglines.json").write_text(
        json.dumps([{"id": "s03e10", "tagline": "Apology is Policy", "revid": 7}])
    )
    _write(episodes, {"id": "s03e10", "logline_generated": "d", "provenance": {}})

    attach_taglines(episodes, overrides)
    first = (episodes / "s03e10.json").read_text()
    attach_taglines(episodes, overrides)
    second = (episodes / "s03e10.json").read_text()
    assert first == second


def test_attach_taglines_preserves_a_human_reviewed_gloss(tmp_data_dir: Path) -> None:
    """The sacred-edits guard extends to the tagline gloss (PRD data rules)."""
    episodes = tmp_data_dir / "episodes"
    overrides = tmp_data_dir / "overrides"
    (overrides / "taglines.json").write_text(
        json.dumps([{"id": "s03e10", "tagline": "Apology is Policy", "revid": 7}])
    )
    _write(
        episodes,
        {
            "id": "s03e10",
            "logline_generated": "d",
            "provenance": {},
            "tagline": {
                "text": "Apology is Policy",
                "is_variant": True,
                "note": "Rob Bowman said it ties to the episode's apology theme.",
                "review_status": "human-reviewed",
                "reviewed_at": "2026-09-12",
                "review_note": None,
            },
        },
    )

    attach_taglines(episodes, overrides)
    record = json.loads((episodes / "s03e10.json").read_text())
    assert record["tagline"]["review_status"] == "human-reviewed"
    assert "apology theme" in record["tagline"]["note"]
