"""Build data/overrides/fox_dvd.json from Wikipedia's Mythology articles (TASKS D-10).

The Fox "Mythology" DVD box sets are the closest thing to an official
mythology-episode canon. Their contents are documented on four CC BY-SA
Wikipedia articles which use the same ``{{Episode list}}`` template as the
season pages, so the brace-balanced parser applies unchanged.

The output is an overrides file: reviewable, hand-editable, committed. Each
entry cites its volume and the exact article revision it came from.

    uv run python tools/record_fox_dvd.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from build._http import HttpClient  # noqa: E402
from build.wikitext import (  # noqa: E402
    extract_episode_rows,
    parse_wikilinks,
    strip_refs,
)

log = logging.getLogger(__name__)

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
VOLUMES = {
    1: "The X-Files Mythology, Volume 1 – Abduction",
    2: "The X-Files Mythology, Volume 2 – Black Oil",
    3: "The X-Files Mythology, Volume 3 – Colonization",
    4: "The X-Files Mythology, Volume 4 – Super Soldiers",
}


def fetch_volume(http: HttpClient, title: str) -> dict:
    response = http.get(
        WIKI_API_URL,
        params={
            "action": "parse",
            "page": title,
            "prop": "wikitext|revid",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        },
    )
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"{title}: {payload['error']}")
    return payload["parse"]


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    entries = []
    with_prodcode = 0
    http = HttpClient()
    for volume, title in VOLUMES.items():
        parse = fetch_volume(http, title)
        rows = extract_episode_rows(parse["wikitext"])
        log.info(
            "volume %d (%r, revid %d): %d rows",
            volume,
            parse["title"],
            parse["revid"],
            len(rows),
        )
        for row in rows:
            titles = parse_wikilinks(row.get("Title", ""))
            # Volume 2 appends <ref> citations to its production codes.
            prod_code = strip_refs(row.get("ProdCode", ""))
            with_prodcode += bool(prod_code)
            entries.append(
                {
                    "title": titles[0] if titles else "",
                    "production_code": prod_code or None,
                    "number_in_set": row.get("EpisodeNumber"),
                    "source_volume": volume,
                    "source_article": parse["title"],
                    "source_revid": parse["revid"],
                }
            )
    out = REPO_ROOT / "data" / "overrides" / "fox_dvd.json"
    out.write_text(json.dumps(entries, indent=1) + "\n")
    log.info(
        "wrote %s: %d entries across %d volumes, %d with production codes",
        out,
        len(entries),
        len(VOLUMES),
        with_prodcode,
    )


if __name__ == "__main__":
    main()
