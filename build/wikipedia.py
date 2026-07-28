"""Step 2 — Wikipedia season pages (TASKS D-07).

11 **serial** requests to ``action=parse`` (PRD §8.1: parallel fetching
returns 429; the shared client throttles to ~1 req/sec). Each payload records
the page's revision id so attribution can point at an exact version.

Never parse ``List_of_The_X-Files_episodes`` — it transcludes the season
pages and its own wikitext contains only the two film rows.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from build._http import HttpClient
from build.wikitext import extract_episode_rows

log = logging.getLogger(__name__)

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
SEASONS = range(1, 12)


def fetch_season(http: HttpClient, season: int) -> dict[str, Any]:
    """Fetch one season page's wikitext plus its revision id."""
    response = http.get(
        WIKI_API_URL,
        params={
            "action": "parse",
            "page": f"The X-Files season {season}",
            "prop": "wikitext|revid",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        },
    )
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"wikipedia season {season}: {payload['error']}")
    parse = payload["parse"]
    return {
        "season": season,
        "page_title": parse["title"],
        "revid": parse["revid"],
        "wikitext": parse["wikitext"],
    }


def write_raw(http: HttpClient, out_dir: Path) -> list[Path]:
    """Fetch every season serially; returns the written paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    total_rows = 0
    for season in SEASONS:
        payload = fetch_season(http, season)
        rows = extract_episode_rows(payload["wikitext"])
        total_rows += len(rows)
        out = out_dir / f"wiki_s{season:02d}.json"
        out.write_text(json.dumps(payload, indent=1) + "\n")
        written.append(out)
        log.info(
            "season %2d: %2d rows, revid %d -> %s",
            season,
            len(rows),
            payload["revid"],
            out.name,
        )
    # Re-derived at run time, never hard-coded (CLAUDE.md).
    log.info("total: %d files, %d episode rows", len(written), total_rows)
    return written


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    write_raw(HttpClient(), Path("data/raw/wiki_seasons"))


if __name__ == "__main__":
    main()
