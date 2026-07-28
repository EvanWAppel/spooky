"""Per-field provenance tests (TASKS E-06; CLAUDE.md: no unattributed fields).

Every ingested field on every committed record must record where it came
from and under what license.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

EPISODES_DIR = Path(__file__).resolve().parent.parent / "data" / "episodes"

# Data fields that must carry provenance when non-null on an episode record.
# The human layer (logline, review_*) is owner-authored by definition, and
# id/season_episode are derived record-keeping.
AUDITED_FIELDS = (
    "tvmaze_id",
    "season",
    "episode",
    "title",
    "air_date",
    "production_code",
    "runtime",
    "rating",
    "label_fox_dvd",
    "label_wikipedia",
    "label_dom111",
    "label_derived",
    "label_contested",
    "label_rationale",
    "imdb_id",
    "wikidata_qid",
    "director",
    "writers",
    "guest_cast",
)


def _records() -> list[dict]:
    files = sorted(EPISODES_DIR.glob("*.json"))
    if not files:
        pytest.skip("data/episodes/ is empty — run the merge first")
    return [json.loads(f.read_text()) for f in files]


def test_every_episode_field_has_sourced_provenance() -> None:
    for record in _records():
        provenance = record["provenance"]
        if "all_fields" in provenance:  # films: one hand-entered block
            entry = provenance["all_fields"]
            assert entry["source"] and entry["license"]
            continue
        missing = [
            field
            for field in AUDITED_FIELDS
            if record.get(field) is not None and field not in provenance
        ]
        assert not missing, f"{record['id']}: unattributed fields {missing}"


def test_every_provenance_entry_names_source_and_license() -> None:
    for record in _records():
        for field, entry in record["provenance"].items():
            assert entry.get("source"), f"{record['id']}.{field}: no source"
            assert entry.get("license"), f"{record['id']}.{field}: no license"


def test_wikipedia_derived_fields_cite_an_exact_revision() -> None:
    """Attribution must point at the exact article version (PRD §8.1)."""
    for record in _records():
        provenance = record["provenance"]
        for field in ("title", "production_code", "label_wikipedia"):
            entry = provenance.get(field)
            if entry and entry["source"] == "Wikipedia":
                assert isinstance(entry.get("revid"), int), (
                    f"{record['id']}.{field}: no revid"
                )
