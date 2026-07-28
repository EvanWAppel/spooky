"""Step 9 — publishable artifacts from the source of truth (TASKS E-08).

Reads ``data/episodes/*.json`` (the committed source of truth) and emits:

- ``data/dist/spooky-episodes.json`` — the full records, one array
- ``data/dist/spooky-episodes.csv``  — flat view (lists joined, provenance
  summarized), for spreadsheet users
- ``data/dist/spooky.sqlite``        — query artifact with an FTS5 index.
  A build output, never committed (PRD §4: gitignored), never edited.

The published dataset is CC BY-SA 4.0 (ShareAlike attaches from the
Wikipedia/TVmaze inputs — CLAUDE.md C6).
"""

from __future__ import annotations

import csv
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CSV_FIELDS = [
    "id",
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
    "logline",
    "review_status",
]


def load_records(episodes_dir: Path) -> list[dict[str, Any]]:
    files = sorted(episodes_dir.glob("*.json"))
    if not files:
        raise RuntimeError(f"no records in {episodes_dir} — run the merge first")
    return [json.loads(f.read_text()) for f in files]


def emit_json(records: list[dict[str, Any]], dist_dir: Path) -> Path:
    out = dist_dir / "spooky-episodes.json"
    out.write_text(json.dumps(records, indent=1, ensure_ascii=False) + "\n")
    return out


def _flatten(record: dict[str, Any]) -> dict[str, Any]:
    row = {field: record.get(field) for field in CSV_FIELDS}
    for list_field in ("director", "writers", "guest_cast"):
        row[list_field] = "; ".join(record.get(list_field) or [])
    return row


def emit_csv(records: list[dict[str, Any]], dist_dir: Path) -> Path:
    out = dist_dir / "spooky-episodes.csv"
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(_flatten(record) for record in records)
    return out


def emit_sqlite(records: list[dict[str, Any]], dist_dir: Path) -> Path:
    out = dist_dir / "spooky.sqlite"
    out.unlink(missing_ok=True)  # regenerable build output, never merged into
    connection = sqlite3.connect(out)
    try:
        connection.execute(
            """CREATE TABLE episodes (
                id TEXT PRIMARY KEY, season INTEGER, episode INTEGER,
                title TEXT, air_date TEXT, production_code TEXT,
                runtime INTEGER, rating REAL,
                label_fox_dvd TEXT, label_wikipedia TEXT, label_dom111 TEXT,
                label_derived TEXT, label_contested INTEGER,
                label_rationale TEXT, imdb_id TEXT, wikidata_qid TEXT,
                director TEXT, writers TEXT, guest_cast TEXT,
                logline TEXT, review_status TEXT, record_json TEXT
            )"""
        )
        connection.execute(
            "CREATE VIRTUAL TABLE episodes_fts USING fts5(id, title, logline)"
        )
        for record in records:
            flat = _flatten(record)
            flat["label_contested"] = int(bool(record["label_contested"]))
            flat["record_json"] = json.dumps(record, ensure_ascii=False)
            columns = ", ".join(flat)
            placeholders = ", ".join(f":{key}" for key in flat)
            connection.execute(
                f"INSERT INTO episodes ({columns}) VALUES ({placeholders})", flat
            )
            connection.execute(
                "INSERT INTO episodes_fts (id, title, logline) VALUES (?, ?, ?)",
                (record["id"], record.get("title") or "", record.get("logline") or ""),
            )
        connection.commit()
    finally:
        connection.close()
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    episodes_dir = Path("data/episodes")
    dist_dir = Path("data/dist")
    dist_dir.mkdir(parents=True, exist_ok=True)
    records = load_records(episodes_dir)
    for emitted in (
        emit_json(records, dist_dir),
        emit_csv(records, dist_dir),
        emit_sqlite(records, dist_dir),
    ):
        log.info("wrote %s (%d records)", emitted, len(records))


if __name__ == "__main__":
    main()
