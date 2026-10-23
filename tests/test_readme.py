"""The README's Live demo line must point at the canonical origin (TASKS C-19, W-02).

The SSR pages, sitemap and robots.txt all advertise ``BASE_URL``; the README is
the first link a reader clicks, so it must agree with them rather than drift.
"""

from __future__ import annotations

import re
from pathlib import Path

from components.ssr import BASE_URL

README = Path(__file__).resolve().parent.parent / "README.md"


def test_live_demo_line_links_the_canonical_origin() -> None:
    lines = [ln for ln in README.read_text().splitlines() if "Live demo" in ln]
    assert len(lines) == 1, f"expected one 'Live demo' line, found {lines!r}"
    urls = re.findall(r"https://[^\s)>\]]+", lines[0])
    assert BASE_URL in [u.rstrip("/") for u in urls], lines[0]
