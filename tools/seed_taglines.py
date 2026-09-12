"""Seed data/overrides/taglines.json (TASKS T-03/T-04; PRD §7, v2).

Scans the article prose already fetched into
``data/raw/article_sections.json`` (step 06, no new network) and proposes the
set of episodes whose opening-title-sequence tagline was swapped from the usual
"The Truth Is Out There". Each entry cites its article and Wikipedia revision
id and quotes the source sentence, so the override is auditable in a ``git
diff`` (CLAUDE.md: reviewable data).

Most variants are extracted verbatim by :func:`build.taglines.extract_variant`.
A few are documented in prose the scanner cannot cleanly quote — those live in
``MANUAL_TAGLINES`` below, exactly as ``seed_creature.py`` keeps its
``NO_CREATURE`` judgment calls. Every manual entry names why it is manual.

Run once; the output is committed and consumed by the merge:

    uv run python tools/seed_taglines.py
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

# Run as a script (`uv run python tools/seed_taglines.py`), Python puts this
# file's own directory on sys.path, not the repo root, so the `build` package is
# unimportable. Put the repo root first so the import resolves as under pytest.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build.taglines import extract_variant  # noqa: E402  (after path bootstrap)

REPO_ROOT = Path(__file__).resolve().parent.parent

log = logging.getLogger(__name__)

# Variants the scanner cannot lift verbatim, keyed by article title. Teliko's
# on-screen card reads "Deceive Inveigle Obfuscate"; Wikipedia states the theme
# as "deceive, inveigle, and obfuscate" in a sentence separate from the one
# noting it "replaces the usual ... tagline", so no single clause quotes the
# card. Flagged for owner confirmation of the exact rendering (T-13).
MANUAL_TAGLINES: dict[str, str] = {
    "Teliko": "Deceive Inveigle Obfuscate",
}


def _clean(sentence: str) -> str:
    """Trim ref/template clutter and leading fragments — human-facing citation."""
    sentence = re.sub(r"\s+", " ", sentence)
    sentence = re.sub(r"</?ref[^>]*>", "", sentence)
    sentence = re.sub(r"\{\{[^}]*\}\}", "", sentence)
    sentence = re.sub(r"^.*?\}\}", "", sentence)  # unmatched leading template tail
    sentence = re.sub(r"^[^A-Z]*", "", sentence.strip()).strip()
    return sentence[:240]


def _source_sentence(prose: str, tagline: str) -> str:
    """The authoritative sentence documenting the swap (for provenance).

    Prefer a sentence naming both the tagline text and "tagline"/"opening
    credits" — that is the one that says *this is the title-card line* — over an
    incidental mention (e.g. "amor fati" also appears in the episode's title).
    """
    sentences = [m.group(0) for m in re.finditer(r"[^.]*\.", prose, re.DOTALL)]
    needle = tagline.lower()
    contexts = ("tagline", "opening credits", "title sequence")
    for require_context in (True, False):
        for sentence in sentences:
            low = sentence.lower()
            if needle in low and (not require_context or any(c in low for c in contexts)):
                return _clean(sentence)
    for sentence in sentences:  # last resort: any "tagline" sentence
        if "tagline" in sentence.lower():
            return _clean(sentence)
    return ""


def _id_by_article(episodes_dir: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in sorted(episodes_dir.glob("*.json")):
        record = json.loads(path.read_text())
        for key in (record.get("enwiki_title"), record.get("title")):
            if key:
                mapping.setdefault(key, record["id"])
    return mapping


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    raw = REPO_ROOT / "data" / "raw"
    sections = json.loads((raw / "article_sections.json").read_text())
    id_by_article = _id_by_article(REPO_ROOT / "data" / "episodes")

    entries = []
    for article, section in sorted(sections.items()):
        prose = (section.get("production") or "") + "\n" + (section.get("themes") or "")
        tagline = MANUAL_TAGLINES.get(article) or extract_variant(prose)
        if not tagline:
            continue
        record_id = id_by_article.get(article)
        if record_id is None:
            raise SystemExit(
                f"article {article!r} documents tagline {tagline!r} but maps to "
                "no episode record — fix the title mapping before seeding"
            )
        entries.append(
            {
                "id": record_id,
                "title": re.sub(r"\s*\(The X-Files\)$", "", article),
                "article": article,
                "tagline": tagline,
                "revid": section.get("revid"),
                "extraction": "manual" if article in MANUAL_TAGLINES else "auto",
                "source_sentence": _source_sentence(prose, tagline),
            }
        )

    missing_manual = set(MANUAL_TAGLINES) - {e["article"] for e in entries}
    if missing_manual:
        raise SystemExit(f"MANUAL_TAGLINES not found in articles: {missing_manual}")

    entries.sort(key=lambda e: e["id"])
    out = REPO_ROOT / "data" / "overrides" / "taglines.json"
    out.write_text(json.dumps(entries, indent=1, ensure_ascii=False) + "\n")
    log.info("wrote %s: %d variant taglines", out, len(entries))


if __name__ == "__main__":
    main()
