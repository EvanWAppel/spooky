"""Step 6 — episode article wikitext via Special:Export (TASKS D-13, D-14).

PRD §8.1: **one** ``Special:Export`` POST with every title, ``curonly=1`` —
firing hundreds of individual ``action=parse`` calls gets half of them 429'd.
Each article's revision id is recorded so attribution points at an exact
version.

Titles come from the Wikidata identifier spine (``enwiki_title``), re-derived
at run time — never a hard-coded list.
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET  # trusted source: Wikipedia's own export
from pathlib import Path
from typing import Any

from build._http import HttpClient

log = logging.getLogger(__name__)

EXPORT_URL = "https://en.wikipedia.org/wiki/Special:Export"
_HEADING = re.compile(r"^==\s*(?P<title>[^=].*?)\s*==\s*$", re.M)
_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[^\]]*)?\]\]")


def article_titles(raw_dir: Path) -> list[str]:
    rows = json.loads((raw_dir / "wikidata.json").read_text())
    return sorted({row["enwiki_title"] for row in rows if row.get("enwiki_title")})


def fetch_export(http: HttpClient, titles: list[str]) -> str:
    """One POST for every title; returns the export XML."""
    log.info("exporting %d articles in one request", len(titles))
    response = http.post(
        EXPORT_URL,
        data={"pages": "\n".join(titles), "curonly": "1", "wpDownload": "1"},
    )
    return response.text


def parse_export(xml_text: str) -> dict[str, dict[str, Any]]:
    """Map article title -> {revid, wikitext} from Special:Export XML."""
    root = ET.fromstring(xml_text)
    namespace = root.tag.split("}")[0].strip("{")
    ns = {"mw": namespace}
    articles: dict[str, dict[str, Any]] = {}
    for page in root.findall("mw:page", ns):
        title = page.findtext("mw:title", namespaces=ns)
        revision = page.find("mw:revision", ns)
        if title is None or revision is None:
            raise RuntimeError(f"export page missing title or revision: {title!r}")
        revid = revision.findtext("mw:id", namespaces=ns)
        wikitext = revision.findtext("mw:text", namespaces=ns) or ""
        if not revid:
            raise RuntimeError(f"article {title!r} has no revision id")
        articles[title] = {"revid": int(revid), "wikitext": wikitext}
    return articles


def extract_section(wikitext: str, heading: str) -> str | None:
    """The body of a level-2 section, or None if the article lacks it."""
    headings = list(_HEADING.finditer(wikitext))
    for index, match in enumerate(headings):
        if match.group("title").strip().lower() == heading.lower():
            start = match.end()
            end = (
                headings[index + 1].start()
                if index + 1 < len(headings)
                else len(wikitext)
            )
            return wikitext[start:end].strip()
    return None


def episode_links(wikitext: str, known_titles: set[str]) -> list[str]:
    """Outbound wikilinks that point at other episode articles."""
    found: list[str] = []
    for match in _WIKILINK.finditer(wikitext):
        target = match.group(1).strip()
        if target in known_titles and target not in found:
            found.append(target)
    return found


def write_raw(http: HttpClient, raw_dir: Path) -> tuple[Path, Path]:
    titles = article_titles(raw_dir)
    xml_text = fetch_export(http, titles)
    xml_out = raw_dir / "articles.xml"
    xml_out.write_text(xml_text)
    log.info("wrote %s (%.1f MB)", xml_out, len(xml_text) / 1e6)

    articles = parse_export(xml_text)
    missing = sorted(set(titles) - set(articles))
    if missing:
        raise RuntimeError(
            f"{len(missing)} requested articles absent from export: {missing[:5]}"
        )

    known = set(articles)
    sections: dict[str, dict[str, Any]] = {
        title: {
            "revid": data["revid"],
            "production": extract_section(data["wikitext"], "Production"),
            "themes": extract_section(data["wikitext"], "Themes"),
            "links": [
                link for link in episode_links(data["wikitext"], known) if link != title
            ],
        }
        for title, data in articles.items()
    }
    sections_out = raw_dir / "article_sections.json"
    sections_out.write_text(json.dumps(sections, indent=1) + "\n")

    edge_count = sum(len(s["links"]) for s in sections.values())
    with_production = sum(1 for s in sections.values() if s["production"])
    with_themes = sum(1 for s in sections.values() if s["themes"])
    log.info(
        "sections: %d articles, %d with Production, %d with Themes, "
        "%d episode-to-episode link edges",
        len(sections),
        with_production,
        with_themes,
        edge_count,
    )
    return xml_out, sections_out


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    write_raw(HttpClient(), Path("data/raw"))


if __name__ == "__main__":
    main()
