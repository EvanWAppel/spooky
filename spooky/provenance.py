"""Re-derive the provenance / pipeline dashboard data from loaded records.

The dashboard (`components/provenance_view.py`, route `/provenance`) surfaces
what the dataset already stores — the source disagreement and per-field
attribution — as the site's data-engineering centrepiece. Every number here is
re-derived from the DataFrame at call time; nothing is hard-coded (CLAUDE.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from spooky.classify import MYTHOLOGY, SOURCE_NAMES
from spooky.values import is_missing


@dataclass(frozen=True)
class Source:
    """One classification source and the column that carries its verdict."""

    column: str
    label: str  # human name shown on the dashboard


# The three sources that vote on the mythology/MOTW split (PRD §5). A null in a
# source column means the source does not cover the record — it abstains — and
# is never counted as coverage (PRD §5.2). Display names come from classify so
# the dashboard and the rationale text name each source identically.
SOURCES: tuple[Source, ...] = (
    Source("label_fox_dvd", SOURCE_NAMES["fox"]),
    Source("label_wikipedia", SOURCE_NAMES["wiki"]),
    Source("label_dom111", SOURCE_NAMES["dom111"]),
)

# A blanket provenance key the film records use in place of per-field entries;
# it is not a field, so the field dictionary skips it.
_BLANKET_PROVENANCE_KEY = "all_fields"


def source_coverage(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Per source: records covered, records abstained on, and mythology count."""
    rows = []
    for source in SOURCES:
        values = df[source.column]
        covered = values.map(lambda value: not is_missing(value))
        rows.append(
            {
                "column": source.column,
                "label": source.label,
                "covers": int(covered.sum()),
                "abstains": int((~covered).sum()),
                "mythology": int((values == MYTHOLOGY).sum()),
            }
        )
    return rows


def contested_breakdown(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Every contested record with its per-source split and rationale."""
    contested = df[df["label_contested"]]
    rows = []
    for _, record in contested.iterrows():
        rows.append(
            {
                "id": record["id"],
                "season_episode": record.get("season_episode"),
                "title": record["title"],
                "label_fox_dvd": _or_none(record.get("label_fox_dvd")),
                "label_wikipedia": _or_none(record.get("label_wikipedia")),
                "label_dom111": _or_none(record.get("label_dom111")),
                "label_derived": record.get("label_derived"),
                "label_rationale": record.get("label_rationale"),
            }
        )
    return rows


def field_provenance(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Aggregate each field's provenance across records into one sorted table.

    A field's ``source``/``license`` are stable across records, but a record
    only carries provenance for the fields it has; aggregating over the whole
    frame gives the complete field dictionary.
    """
    fields: dict[str, dict[str, Any]] = {}
    if "provenance" not in df.columns:
        return []
    for provenance in df["provenance"]:
        if not isinstance(provenance, dict):
            continue
        for field, meta in provenance.items():
            if field == _BLANKET_PROVENANCE_KEY:
                continue  # the films' blanket note, not a field
            if not isinstance(meta, dict):
                continue  # e.g. the sample fixtures' free-text "fixture" note
            entry = fields.setdefault(
                field,
                {"field": field, "sources": set(), "licenses": set(), "has_revid": False},
            )
            if meta.get("source"):
                entry["sources"].add(meta["source"])
            if meta.get("license"):
                entry["licenses"].add(meta["license"])
            if meta.get("revid") is not None:
                entry["has_revid"] = True
    return [
        {
            "field": entry["field"],
            "sources": sorted(entry["sources"]),
            "licenses": sorted(entry["licenses"]),
            "has_revid": entry["has_revid"],
        }
        for entry in sorted(fields.values(), key=lambda entry: entry["field"])
    ]


def _or_none(value: Any) -> Any:
    """Collapse a missing value (None/NaN/NA) to None for the split table."""
    return None if is_missing(value) else value
