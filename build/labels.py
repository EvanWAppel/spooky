"""Step 4 — dom111 mythology/MOTW labels (TASKS D-09).

Fetches ``data/episode-list-data.json`` from dom111/xfiles-episode-picker by
**pinned blob SHA**, so upstream edits can never silently change our labels —
if the blob disappears, this fails loudly and the pin gets reviewed, not
papered over.

License note (PRD §8.1): the repo wrapper is MIT, but the payload is
TVmaze-derived and stays CC BY-SA — attribute both.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from build._http import HttpClient

log = logging.getLogger(__name__)

# data/episode-list-data.json as of 2026-07-27. Re-pin deliberately, never
# implicitly: fetch HEAD, diff the labels, update this constant in its own
# commit.
BLOB_SHA = "3fd676dacc8392a0cc851f3b1976076c439c66f5"
BLOB_URL = (
    "https://api.github.com/repos/dom111/xfiles-episode-picker/git/blobs/" + BLOB_SHA
)
LABEL_FIELD = "episode_type"


def fetch_labels(http: HttpClient) -> list[dict[str, Any]]:
    """Fetch the pinned payload; returns the full record list."""
    response = http.get(BLOB_URL, params=None)
    payload = response.json()
    if payload.get("encoding") != "base64":
        raise RuntimeError(
            f"unexpected blob encoding {payload.get('encoding')!r} for {BLOB_SHA}"
        )
    import base64

    records = json.loads(base64.b64decode(payload["content"]))
    counts = Counter(record[LABEL_FIELD] for record in records)
    # Counts are logged re-derived, never asserted against hard-coded numbers
    # here — the test fixture pins the expectation (CLAUDE.md).
    log.info("dom111 labels: %s across %d records", dict(counts), len(records))
    return records


def write_raw(http: HttpClient, raw_dir: Path) -> Path:
    records = fetch_labels(http)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out = raw_dir / "dom111.json"
    out.write_text(json.dumps(records, indent=1) + "\n")
    log.info("wrote %s (%d records)", out, len(records))
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    write_raw(HttpClient(), Path("data/raw"))


if __name__ == "__main__":
    main()
