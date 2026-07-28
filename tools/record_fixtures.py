"""Record real API payloads into tests/fixtures/ (TASKS B-02, B-03).

Run once, commit the output. Parser tests run offline against these files;
the separate `-m network` suite hits the live APIs to catch upstream drift.

    uv run python tools/record_fixtures.py

Wikipedia requests carry a descriptive User-Agent and are throttled to
~1 req/sec (PRD §8.1 — generic agents get blocked, parallel fetching 429s).
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
USER_AGENT = os.getenv("WIKI_USER_AGENT", "spooky/0.1 (appelew@gmail.com)")

TVMAZE_EPISODES_URL = "https://api.tvmaze.com/shows/430/episodes"
WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
# The known parser edge cases (TASKS B-03): S3 template capitalization,
# S10 + S11 revival rows (6 + 10 episodes).
WIKI_SEASONS = [3, 10, 11]


def record_tvmaze(client: httpx.Client) -> None:
    # PRD §8.1: no ?specials=1 — it returns 222 records and breaks the count.
    response = client.get(TVMAZE_EPISODES_URL)
    response.raise_for_status()
    episodes = response.json()
    out = FIXTURES / "tvmaze_episodes.json"
    out.write_text(json.dumps(episodes, indent=1) + "\n")
    log.info("tvmaze: %d records -> %s", len(episodes), out.name)


def record_wiki_season(client: httpx.Client, season: int) -> None:
    response = client.get(
        WIKI_API_URL,
        params={
            "action": "parse",
            "page": f"The X-Files season {season}",
            "prop": "wikitext",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        },
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"wikipedia season {season}: {payload['error']}")
    wikitext = payload["parse"]["wikitext"]
    out = FIXTURES / f"wiki_s{season:02d}.txt"
    out.write_text(wikitext)
    log.info(
        "wikipedia: season %d, page %r, %d chars -> %s",
        season,
        payload["parse"]["title"],
        len(wikitext),
        out.name,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    FIXTURES.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as client:
        record_tvmaze(client)
        for season in WIKI_SEASONS:
            time.sleep(1)  # PRD §8.1: serial, ~1 req/sec
            record_wiki_season(client, season)


if __name__ == "__main__":
    main()
