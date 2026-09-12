"""Opening-title taglines — the build layer (TASKS T-04/T-05; PRD §7, v2).

Every episode's opening-credits tagline is attached at merge time. The variant
episodes — the ones where the usual "The Truth Is Out There" was swapped — live
in a curated ``data/overrides/taglines.json``, sourced from each episode's
Wikipedia *Production* / *Conception and writing* section (the prose step 06
already fetched into ``data/raw/article_sections.json``). Every entry cites the
article and its revision id.

Why a curated override rather than a live prose scrape at build time? The prose
phrasing is too varied and too false-positive-prone to trust blind — the same
"tagline" word describes Fox *advertising* taglines ("Don't watch it alone"),
the *film's* marketing line, and the Ten Thirteen "I Made This" voice tag, none
of which are the title card. So this mirrors the ``creature.json`` pattern:
``tools/seed_taglines.py`` extracts candidates, the override is committed and
reviewable, and :func:`find_drift` re-checks the prose on every build and
**fails loudly** if a documented change is missing from the override — the
"re-derive, don't trust" guarantee, without the brittleness (CLAUDE.md).

The variant set is never hard-coded as a count; it is exactly the length of the
override, and the merge re-derives ``is_variant`` per record.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from spooky.taglines import DEFAULT_TAGLINE, is_variant

log = logging.getLogger(__name__)

_CC_BY_SA = "CC BY-SA 4.0"

# A quoted / italicised / wikilinked phrase — the three ways Wikipedia renders a
# tagline in prose. ``.+?`` (not ``[^']+``) so internal apostrophes survive, as
# in Anasazi's Navajo line.
_CAP = r"""(?:["“](.+?)["”]|''(.+?)''|\[\[(?:[^\]|]+\|)?([^\]]+?)\]\])"""

# Each pattern requires opening-credits / title-sequence / "this episode"
# context so an advertising or film tagline in the same article cannot match.
_PATTERNS = [
    rf"tagline for (?:this|the) episode is {_CAP}",
    rf"tagline that (?:usually )?appears (?:after|in) the opening credits"
    rf"(?: for this episode)? is {_CAP}",
    rf"tagline[^.]*?(?:switched|changed) from[^.]*?to {_CAP}",
    rf"(?:tagline|opening credits)[^.]*?replaced (?:the usual [^.]*?with |with )?{_CAP}",
    rf"usual [^.]*?tagline[^.]*?replaced[^.]*?{_CAP}",
    rf"translated into \w+:\s*{_CAP}",
]


def _strip_markup(phrase: str) -> str:
    """Reduce ``[[Eppur si muove|E pur si muove]]`` / ``''amor fati''`` to text."""
    phrase = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+?)\]\]", r"\1", phrase)
    return phrase.replace("''", "").strip().strip('",.').strip()


def extract_variant(prose: str) -> str | None:
    """The variant tagline documented in an article's prose, or ``None``.

    Shared by the seed tool (to propose the override) and :func:`find_drift`
    (to police it). Returns ``None`` when nothing is documented — the common
    case, which simply means the episode carries the default.
    """
    if not prose:
        return None
    for pattern in _PATTERNS:
        match = re.search(pattern, prose, re.IGNORECASE | re.DOTALL)
        if match:
            phrase = _strip_markup(next(group for group in match.groups() if group))
            # A sentence about the default ("...usual 'The Truth is Out There'")
            # can match the loose patterns; the default is not a variant.
            if is_variant(phrase):
                return phrase
    return None


def load_overrides(overrides_dir: Path) -> dict[str, dict[str, Any]]:
    """The curated variant taglines, keyed by record id. Empty if absent."""
    path = Path(overrides_dir) / "taglines.json"
    if not path.exists():
        log.warning("no taglines override at %s — all episodes get the default", path)
        return {}
    return {entry["id"]: entry for entry in json.loads(path.read_text())}


def build_tagline(record_id: str, overrides: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The nested ``tagline`` object for a record (PRD §7 data model).

    ``is_variant`` is DERIVED here, never taken from the override, so the
    override cannot lie about it. The gloss lifecycle fields start empty — that
    work (T-06/T-07) lands with the logline review pass.
    """
    entry = overrides.get(record_id)
    text = entry["tagline"] if entry else DEFAULT_TAGLINE
    return {
        "text": text,
        "is_variant": is_variant(text),
        "broadcast_only": (entry or {}).get("broadcast_only"),
        "note_generated": None,
        "note": None,
        "review_status": None,
        "reviewed_at": None,
        "review_note": None,
    }


def tagline_provenance(
    record_id: str, overrides: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Per-field provenance for ``tagline.text`` (PRD §8.2)."""
    entry = overrides.get(record_id)
    if entry:
        return {"source": "Wikipedia", "license": _CC_BY_SA, "revid": entry["revid"]}
    return {
        "source": "series default (no per-episode change documented on Wikipedia)",
        "license": _CC_BY_SA,
    }


# The human-owned layer of the tagline gloss — never overwritten once reviewed
# (the sacred-edits guard, mirroring merge.py's HUMAN_OWNED_FIELDS). The gloss
# review lifecycle lands with the logline pass (T-06/T-07); until then no record
# has a reviewed tagline, so this simply future-proofs the attach step.
HUMAN_OWNED_TAGLINE = ("note", "review_status", "reviewed_at", "review_note")


def _place_tagline(record: dict[str, Any], tagline: dict[str, Any]) -> dict[str, Any]:
    """Record with ``tagline`` inserted just before ``logline_generated``.

    Any existing ``tagline`` is dropped and re-inserted, so re-runs are
    idempotent and the field order matches a from-scratch merge.
    """
    out: dict[str, Any] = {}
    for key, value in record.items():
        if key == "tagline":
            continue
        if key == "logline_generated" and "tagline" not in out:
            out["tagline"] = tagline
        out[key] = value
    if "tagline" not in out:
        out["tagline"] = tagline
    return out


def attach_taglines(episodes_dir: Path, overrides_dir: Path) -> tuple[int, int]:
    """Add / refresh the ``tagline`` object on every committed record, in place.

    This step owns ONLY ``tagline`` and ``provenance["tagline.text"]`` — it
    runs after the merge and leaves loglines and every other field untouched, so
    it can refresh taglines without re-running the (API-billed) logline step. A
    human-reviewed gloss is carried forward; everything else is re-derived from
    the override. Returns ``(records, variants)``.
    """
    overrides = load_overrides(overrides_dir)
    files = sorted(Path(episodes_dir).glob("*.json"))
    if not files:
        raise RuntimeError(f"no records in {episodes_dir} — run the merge first")
    variants = 0
    for path in files:
        record = json.loads(path.read_text())
        tagline = build_tagline(record["id"], overrides)
        existing = record.get("tagline")
        if isinstance(existing, dict) and (
            existing.get("review_status") == "human-reviewed"
        ):
            for field in HUMAN_OWNED_TAGLINE:
                tagline[field] = existing.get(field)
        record = _place_tagline(record, tagline)
        record.setdefault("provenance", {})["tagline.text"] = tagline_provenance(
            record["id"], overrides
        )
        path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
        variants += int(tagline["is_variant"])
    return len(files), variants


def find_drift(
    overrides: dict[str, dict[str, Any]],
    sections: dict[str, dict[str, Any]],
    id_by_article: dict[str, str],
) -> list[str]:
    """Articles whose prose documents a tagline change absent from the override.

    This is the "re-derive, don't trust" guard: if Wikipedia documents a swap
    for an episode the override doesn't list, the override has gone stale and
    the build must fail rather than silently ship the default (CLAUDE.md: *do
    not hide errors*). An override entry with no id mapping is also drift.
    """
    drift: list[str] = []
    for article, entry in sections.items():
        prose = (entry.get("production") or "") + "\n" + (entry.get("themes") or "")
        variant = extract_variant(prose)
        if variant is None:
            continue
        record_id = id_by_article.get(article)
        if record_id is None:
            drift.append(
                f"{article!r}: documents tagline {variant!r} but maps to no record"
            )
        elif record_id not in overrides:
            drift.append(
                f"{article!r} ({record_id}): documents tagline {variant!r}, "
                "missing from taglines.json"
            )
    return drift


def _id_by_article(episodes_dir: Path) -> dict[str, str]:
    """Map every Wikipedia article title (as keyed in article_sections) to its
    record id, via the merged episodes' ``enwiki_title`` / ``title``."""
    mapping: dict[str, str] = {}
    for path in sorted(episodes_dir.glob("*.json")):
        record = json.loads(path.read_text())
        for key in (record.get("enwiki_title"), record.get("title")):
            if key:
                mapping.setdefault(key, record["id"])
    return mapping


def main() -> None:
    """Pipeline step ``taglines`` — attach taglines in place, then audit drift.

    Runs after the merge (``uv run python -m build --only taglines``): it writes
    the tagline object onto every record, then re-derives the drift check
    against the current article prose and fails loudly if the override has gone
    stale (CLAUDE.md: do not hide errors).
    """
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    episodes_dir = Path("data/episodes")
    overrides_dir = Path("data/overrides")
    total, variants = attach_taglines(episodes_dir, overrides_dir)

    overrides = load_overrides(overrides_dir)
    sections = json.loads((Path("data/raw") / "article_sections.json").read_text())
    id_by_article = _id_by_article(episodes_dir)

    # An override id that resolves to no article/record is drift too.
    articles_by_id = {rid: art for art, rid in id_by_article.items()}
    stale = [
        f"{rid}: {entry.get('tagline')!r} — no matching article/record"
        for rid, entry in overrides.items()
        if rid not in articles_by_id
    ]
    drift = find_drift(overrides, sections, id_by_article) + stale
    if drift:
        raise SystemExit(
            "tagline override drift — the article prose and taglines.json "
            "disagree:\n  " + "\n  ".join(sorted(drift))
        )

    log.info(
        "taglines: attached to %d records, %d variants, no drift (default: %r)",
        total,
        variants,
        DEFAULT_TAGLINE,
    )


if __name__ == "__main__":
    main()
