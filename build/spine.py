"""Step 1 — the TVmaze episode spine (TASKS D-01).

One call, no key, 218 records. PRD §8.1: **never** pass ``?specials=1`` — it
returns 222 records and silently breaks every downstream count. Everything in
the merge keys on the TVmaze ``id``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from build._http import HttpClient

log = logging.getLogger(__name__)

TVMAZE_EPISODES_URL = "https://api.tvmaze.com/shows/430/episodes"


def fetch_episodes(http: HttpClient) -> list[dict[str, Any]]:
    """Fetch the raw episode list. No params — see the module docstring."""
    response = http.get(TVMAZE_EPISODES_URL)
    episodes = response.json()
    log.info("tvmaze spine: %d episodes", len(episodes))
    return episodes


def write_raw(http: HttpClient, raw_dir: Path) -> Path:
    """Fetch and write the raw payload verbatim; returns the output path."""
    episodes = fetch_episodes(http)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out = raw_dir / "tvmaze_episodes.json"
    out.write_text(json.dumps(episodes, indent=1) + "\n")
    log.info("wrote %s (%d records)", out, len(episodes))
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    write_raw(HttpClient(), Path("data/raw"))


if __name__ == "__main__":
    main()
