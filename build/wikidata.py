"""Step 3 — Wikidata identifier spine (TASKS D-08).

One SPARQL query, CC0, no attribution obligations (PRD §8.1). Used for the
ID spine only: enwiki article title and IMDb id (P345) per episode. The
series QID Q2744 was resolved from the series' own IMDb id (tt0106179), not
assumed.

Wikidata holds three items for "The Truth" — one merged item carrying the
identifiers and two empty split shells. The hand ruling lives in
``data/overrides/wikidata_dupes.json`` and is applied here, dropping the
shells so downstream sees one row per Wikidata subject.

Per-episode TMDB ids are deliberately absent: no well-populated Wikidata
property exists for them, and nothing in v1 needs one (the watch link is
season-level).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from build._http import HttpClient

log = logging.getLogger(__name__)

SPARQL_URL = "https://query.wikidata.org/sparql"
QUERY = """
SELECT ?ep ?epLabel ?imdb ?enwiki WHERE {
  ?ep wdt:P31 wd:Q21191270 ; wdt:P179 wd:Q2744 .
  OPTIONAL { ?ep wdt:P345 ?imdb }
  OPTIONAL {
    ?article schema:about ?ep ;
             schema:isPartOf <https://en.wikipedia.org/> ;
             schema:name ?enwiki
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def fetch_rows(http: HttpClient) -> list[dict[str, Any]]:
    response = http.get(SPARQL_URL, params={"query": QUERY, "format": "json"})
    bindings = response.json()["results"]["bindings"]
    rows = [
        {
            "qid": b["ep"]["value"].rsplit("/", 1)[1],
            "label": b.get("epLabel", {}).get("value"),
            "imdb_id": b.get("imdb", {}).get("value"),
            "enwiki_title": b.get("enwiki", {}).get("value"),
        }
        for b in bindings
    ]
    log.info("wikidata: %d rows", len(rows))
    return rows


def apply_dupe_ruling(
    rows: list[dict[str, Any]], overrides_path: Path
) -> list[dict[str, Any]]:
    ruling = json.loads(overrides_path.read_text())
    drop = set(ruling["drop"])
    kept = [row for row in rows if row["qid"] not in drop]
    dropped = len(rows) - len(kept)
    if dropped != len(drop):
        raise RuntimeError(
            f"dupe ruling expected to drop {sorted(drop)} but matched "
            f"{dropped} rows — the upstream duplicates changed; re-review "
            f"{overrides_path}"
        )
    log.info("dupe ruling: dropped %d shell items", dropped)
    return kept


def write_raw(http: HttpClient, raw_dir: Path, overrides_dir: Path) -> Path:
    rows = apply_dupe_ruling(fetch_rows(http), overrides_dir / "wikidata_dupes.json")
    qids = [row["qid"] for row in rows]
    if len(qids) != len(set(qids)):
        raise RuntimeError("duplicate qids survived the dupe ruling")
    raw_dir.mkdir(parents=True, exist_ok=True)
    out = raw_dir / "wikidata.json"
    out.write_text(json.dumps(rows, indent=1) + "\n")
    log.info(
        "wrote %s (%d rows; %d with imdb, %d with enwiki)",
        out,
        len(rows),
        sum(1 for r in rows if r["imdb_id"]),
        sum(1 for r in rows if r["enwiki_title"]),
    )
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    write_raw(HttpClient(), Path("data/raw"), Path("data/overrides"))


if __name__ == "__main__":
    main()
