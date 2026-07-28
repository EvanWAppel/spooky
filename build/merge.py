"""Step 7 — the merge: raw sources → data/episodes/*.json (TASKS E-03, E-05, E-06).

Policies, decided once (PRD §8.1 step 07):

- **TVmaze's shape wins**: 218 episode rows. Wikipedia merges "The Truth"
  into one ``<hr>``-joined row; ``expand_wiki_rows`` splits it and duplicates
  Wikipedia's values across both TVmaze rows.
- **Joins never touch TVmaze titles.** Wikipedia rows key on
  ``(season, number)``; Wikidata joins on the wiki row's link target (both
  Wikipedia-side), so the Amor Fati spelling mismatch cannot cause a miss.
  TVmaze-name fallback exists only for rows with no Wikipedia link.
- **Writers/directors are TVmaze-primary** (the Writer∪Story∪Teleplay union,
  218/218 verified) — Wikipedia's credit fields hide nested
  ``{{StoryTeleplay}}`` templates that drop unlinked names. Deviation from
  PRD §8.2's "Wikipedia primary" noted here and in each record's provenance.
- **Human-reviewed content is sacred** (E-05): ``write_record`` refuses to
  change any human-owned field on a reviewed record — it raises with a diff,
  it never skips silently.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from build.wikitext import is_mythology_flagged, split_multi_value
from spooky.classify import derive_label

log = logging.getLogger(__name__)

SERIES_TMDB_ID = 4087
# The Fox "Mythology" DVD sets cover the original run only (released 2005).
FOX_COVERED_SEASONS = range(1, 10)
HUMAN_OWNED_FIELDS = ("logline", "review_status", "reviewed_at", "review_note")

_CC_BY_SA = "CC BY-SA 4.0"
_SOURCES = {
    "tvmaze": {"source": "TVmaze", "license": _CC_BY_SA},
    "wikipedia": {"source": "Wikipedia", "license": _CC_BY_SA},
    "wikidata": {"source": "Wikidata", "license": "CC0"},
    "dom111": {
        "source": "dom111/xfiles-episode-picker (TVmaze-derived)",
        "license": f"MIT wrapper, data {_CC_BY_SA}",
    },
    "fox_dvd": {
        "source": "Fox Mythology DVD sets, via their Wikipedia articles",
        "license": _CC_BY_SA,
    },
    "derived": {"source": "derived by this project", "license": _CC_BY_SA},
    "owner": {"source": "hand-entered by the owner", "license": _CC_BY_SA},
}


class ReviewGuardError(RuntimeError):
    """A pipeline step tried to change human-reviewed content."""


def wiki_link_target(value: str) -> str | None:
    """The article title a ``[[target|display]]`` link points at."""
    start = value.find("[[")
    if start == -1:
        return None
    end = value.find("]]", start)
    if end == -1:
        return None
    inner = value[start + 2 : end]
    return inner.split("|", 1)[0].split("#", 1)[0].strip()


def expand_wiki_rows(
    rows_by_season: dict[int, list[dict[str, str]]],
) -> dict[tuple[int, int], dict[str, str]]:
    """Key rows on (season, number), splitting ``<hr>``-merged multi-rows.

    A Wikipedia row whose ``EpisodeNumber2`` holds N ``<hr>``-joined numbers
    becomes N keyed rows. Fields with matching part counts (``ProdCode``)
    split alongside; everything else is duplicated (the two-parter policy).
    """
    keyed: dict[tuple[int, int], dict[str, str]] = {}
    for season, rows in rows_by_season.items():
        for row in rows:
            numbers = split_multi_value(row.get("EpisodeNumber2", ""))
            for index, number_text in enumerate(numbers):
                if not number_text.isdigit():
                    raise ValueError(
                        f"season {season}: non-numeric EpisodeNumber2 part "
                        f"{number_text!r} in {row.get('Title', '?')!r}"
                    )
                part = dict(row)
                for field in ("EpisodeNumber", "EpisodeNumber2", "ProdCode"):
                    parts = split_multi_value(row.get(field, ""))
                    if len(parts) == len(numbers):
                        part[field] = parts[index]
                key = (season, int(number_text))
                if key in keyed:
                    raise ValueError(f"duplicate wiki row for {key}")
                keyed[key] = part
    return keyed


def _label_variants(tvmaze_name: str) -> list[str]:
    """Names to try against Wikidata labels, most specific first.

    TVmaze names two-parters ``"X (1)"``/``"X (2)"``; Wikidata labels the
    same items ``"X"``/``"X II"``.
    """
    variants = [tvmaze_name]
    if tvmaze_name.endswith(" (1)"):
        variants.append(tvmaze_name.removesuffix(" (1)"))
    elif tvmaze_name.endswith(" (2)"):
        base = tvmaze_name.removesuffix(" (2)")
        variants.extend([f"{base} II", base])
    return variants


def join_wikidata(
    wiki_row: dict[str, str] | None,
    *,
    tvmaze_name: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Wikidata row for an episode: by wiki link target, else by label."""
    by_title = {row["enwiki_title"]: row for row in rows if row.get("enwiki_title")}
    if wiki_row is not None:
        target = wiki_link_target(wiki_row.get("Title", ""))
        if target and target in by_title:
            return by_title[target]
    by_label = {row["label"]: row for row in rows if row.get("label")}
    for variant in _label_variants(tvmaze_name):
        if variant in by_label:
            return by_label[variant]
    return None


def _diff_line(field: str, old: Any, new: Any) -> str:
    return f"  {field}:\n    on disk:  {old!r}\n    incoming: {new!r}"


def guard_human_fields(existing: dict[str, Any], candidate: dict[str, Any]) -> None:
    """Raise if ``candidate`` would change human-owned fields on a reviewed record."""
    if existing.get("review_status") != "human-reviewed":
        return
    changed = [
        field
        for field in HUMAN_OWNED_FIELDS
        if field in candidate and candidate[field] != existing.get(field)
    ]
    if changed:
        diff = "\n".join(_diff_line(f, existing.get(f), candidate[f]) for f in changed)
        raise ReviewGuardError(
            f"record {existing.get('id')!r} is human-reviewed; refusing to "
            f"change {changed}. Nothing was written.\n{diff}"
        )


def write_record(episodes_dir: Path, record: dict[str, Any]) -> Path:
    """Write one record, preserving the human layer of any existing file.

    Machine refreshes carry ``review_status: "unreviewed"``; if the record on
    disk is human-reviewed, its human-owned fields are carried forward
    untouched. A candidate that *explicitly* asserts different human-owned
    values against a reviewed record trips the guard and raises.
    """
    episodes_dir.mkdir(parents=True, exist_ok=True)
    out = episodes_dir / f"{record['id']}.json"
    candidate = dict(record)
    if out.exists():
        existing = json.loads(out.read_text())
        if existing.get("review_status") == "human-reviewed":
            if candidate.get("review_status") == "human-reviewed":
                guard_human_fields(existing, candidate)
            for field in HUMAN_OWNED_FIELDS:
                candidate[field] = existing.get(field)
    out.write_text(json.dumps(candidate, indent=1, ensure_ascii=False) + "\n")
    return out


def _norm_title(title: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]", "", title.lower())


def _fox_label(season: int, title: str, fox_titles: set[str]) -> str | None:
    """Fox set membership, joined by title ONLY — never by production code.

    Found live: the Mythology volume articles number their production codes
    on a different convention than the season pages (the volumes say Deep
    Throat is 1X02; the season page — and the actual booklet, where the
    pilot is 1X79 — says 1X01). A code join therefore silently labels each
    entry's *neighbor* episode. Titles are exact article wikilinks, unique
    across all four volumes, and verified complete by ``run_merge``.
    """
    if season not in FOX_COVERED_SEASONS:
        return None
    if _norm_title(title) in fox_titles:
        return "mythology"
    return "not-listed"


def _provenance(wiki_revid: int | None, has_wikidata: bool) -> dict[str, Any]:
    p: dict[str, Any] = {
        "tvmaze_id": _SOURCES["tvmaze"],
        "season": _SOURCES["tvmaze"],
        "episode": _SOURCES["tvmaze"],
        "air_date": _SOURCES["tvmaze"],
        "runtime": _SOURCES["tvmaze"],
        "rating": _SOURCES["tvmaze"],
        "guest_cast": _SOURCES["tvmaze"],
        "director": _SOURCES["tvmaze"],
        "writers": _SOURCES["tvmaze"],
        "label_dom111": _SOURCES["dom111"],
        "label_derived": _SOURCES["derived"],
        "label_contested": _SOURCES["derived"],
        "label_rationale": _SOURCES["derived"],
    }
    if wiki_revid is not None:
        wiki = dict(_SOURCES["wikipedia"], revid=wiki_revid)
        p["title"] = wiki
        p["production_code"] = wiki
        p["label_wikipedia"] = wiki
        p["label_fox_dvd"] = dict(_SOURCES["fox_dvd"])
    if has_wikidata:
        p["imdb_id"] = _SOURCES["wikidata"]
        p["wikidata_qid"] = _SOURCES["wikidata"]
    return p


def build_episode_record(
    episode: dict[str, Any],
    *,
    wiki_row: dict[str, str] | None,
    wiki_revid: int | None,
    wikidata_row: dict[str, Any] | None,
    dom111_label: str,
    fox_titles: set[str],
    writers: list[str],
    directors: list[str],
    guest_cast: list[str],
    has_creature: bool,
) -> dict[str, Any]:
    season, number = episode["season"], episode["number"]
    production_code = (wiki_row or {}).get("ProdCode") or None
    title = None
    if wiki_row is not None:
        from build.wikitext import parse_wikilinks

        names = parse_wikilinks(wiki_row.get("Title", ""))
        title = names[0] if names else None
    label_wikipedia = (
        ("mythology" if is_mythology_flagged(wiki_row) else "not-flagged")
        if wiki_row is not None
        else None
    )
    label_fox = _fox_label(season, title or episode["name"], fox_titles)
    label_dom111 = "mythology" if dom111_label == "mythology" else "motw"
    derived, contested, rationale = derive_label(
        fox=label_fox,
        wiki=label_wikipedia,
        dom111=label_dom111,
        has_creature=has_creature,
    )
    rating = (episode.get("rating") or {}).get("average")
    return {
        "id": f"s{season:02d}e{number:02d}",
        "tvmaze_id": episode["id"],
        "season": season,
        "episode": number,
        "title": title or episode["name"],
        "air_date": episode.get("airdate") or None,
        "production_code": production_code,
        "runtime": episode.get("runtime"),
        "rating": rating,
        "label_fox_dvd": label_fox,
        "label_wikipedia": label_wikipedia,
        "label_dom111": label_dom111,
        "label_derived": derived,
        "label_contested": contested,
        "label_rationale": rationale,
        "imdb_id": (wikidata_row or {}).get("imdb_id"),
        "wikidata_qid": (wikidata_row or {}).get("qid"),
        "enwiki_title": (wikidata_row or {}).get("enwiki_title"),
        "tmdb_id": SERIES_TMDB_ID,
        "tmdb_movie_id": None,
        "director": directors,
        "writers": writers,
        "guest_cast": guest_cast,
        "logline_generated": None,
        "logline": None,
        "review_status": "unreviewed",
        "reviewed_at": None,
        "review_note": None,
        "provenance": _provenance(wiki_revid, wikidata_row is not None),
    }


def build_film_record(film: dict[str, Any], has_creature: bool) -> dict[str, Any]:
    derived, contested, rationale = derive_label(
        fox=film["label_fox_dvd"],
        wiki=film["label_wikipedia"],
        dom111=film["label_dom111"],
        has_creature=has_creature,
    )
    return {
        "id": film["id"],
        "tvmaze_id": None,
        "season": None,
        "episode": None,
        "title": film["title"],
        "air_date": film["release_date"],
        "production_code": None,
        "runtime": film["runtime"],
        "rating": None,
        "label_fox_dvd": film["label_fox_dvd"],
        "label_wikipedia": film["label_wikipedia"],
        "label_dom111": film["label_dom111"],
        "label_derived": derived,
        "label_contested": contested,
        "label_rationale": rationale,
        "imdb_id": film["imdb_id"],
        "wikidata_qid": film["wikidata_qid"],
        "enwiki_title": film["enwiki_title"],
        "tmdb_id": None,
        "tmdb_movie_id": film["tmdb_movie_id"],
        "director": film["director"],
        "writers": film["writers"],
        "guest_cast": [],
        "logline_generated": None,
        "logline": None,
        "review_status": "unreviewed",
        "reviewed_at": None,
        "review_note": None,
        "provenance": {
            "all_fields": dict(
                _SOURCES["owner"],
                note="hand-entered from Wikipedia/Wikidata, see films.json",
            )
        },
    }


def run_merge(raw_dir: Path, overrides_dir: Path, episodes_dir: Path) -> list[Path]:
    from build.people import extract_directors, extract_writers
    from build.wikitext import extract_episode_rows

    spine = json.loads((raw_dir / "tvmaze_episodes.json").read_text())
    rows_by_season: dict[int, list[dict[str, str]]] = {}
    revid_by_season: dict[int, int] = {}
    for path in sorted((raw_dir / "wiki_seasons").glob("wiki_s*.json")):
        payload = json.loads(path.read_text())
        rows_by_season[payload["season"]] = extract_episode_rows(payload["wikitext"])
        revid_by_season[payload["season"]] = payload["revid"]
    wiki_rows = expand_wiki_rows(rows_by_season)
    wikidata_rows = json.loads((raw_dir / "wikidata.json").read_text())
    dom111 = {
        r["id"]: r["episode_type"]
        for r in json.loads((raw_dir / "dom111.json").read_text())
    }
    guestcast = json.loads((raw_dir / "guestcast.json").read_text())
    guestcrew = json.loads((raw_dir / "guestcrew.json").read_text())
    fox_entries = json.loads((overrides_dir / "fox_dvd.json").read_text())
    fox_titles = {_norm_title(e["title"]) for e in fox_entries if e.get("title")}
    creature = {
        e["id"]: e["has_creature"]
        for e in json.loads((overrides_dir / "creature.json").read_text())
    }
    films = json.loads((overrides_dir / "films.json").read_text())

    # Re-derived sanity checks — counts are compared between sources, never
    # against hard-coded literals (CLAUDE.md).
    if len(wiki_rows) != len(spine):
        raise RuntimeError(
            f"wiki rows ({len(wiki_rows)}) != spine episodes ({len(spine)}) "
            "after two-parter expansion — the upstream tables shifted"
        )

    written: list[Path] = []
    wikidata_misses: list[str] = []
    episode_titles_seen: set[str] = set()
    for episode in spine:
        key = (episode["season"], episode["number"])
        wiki_row = wiki_rows.get(key)
        if wiki_row is None:
            raise RuntimeError(f"no Wikipedia row for {key} ({episode['name']!r})")
        wikidata_row = join_wikidata(
            wiki_row, tvmaze_name=episode["name"], rows=wikidata_rows
        )
        if wikidata_row is None:
            wikidata_misses.append(episode["name"])
        record_id = f"s{episode['season']:02d}e{episode['number']:02d}"
        crew = guestcrew[str(episode["id"])]
        record = build_episode_record(
            episode,
            wiki_row=wiki_row,
            wiki_revid=revid_by_season[episode["season"]],
            wikidata_row=wikidata_row,
            dom111_label=dom111[episode["id"]],
            fox_titles=fox_titles,
            writers=extract_writers(crew),
            directors=extract_directors(crew),
            guest_cast=[
                m.get("person", {}).get("name")
                for m in guestcast[str(episode["id"])]
                if m.get("person", {}).get("name")
            ],
            has_creature=creature[record_id],
        )
        episode_titles_seen.add(_norm_title(record["title"]))
        written.append(write_record(episodes_dir, record))

    # The fox join is title-only, so every fox entry must find its episode —
    # an unmatched title means a rename upstream and silently-lost labels.
    fox_unmatched = fox_titles - episode_titles_seen
    if fox_unmatched:
        raise RuntimeError(
            f"{len(fox_unmatched)} Fox DVD titles matched no episode: "
            f"{sorted(fox_unmatched)[:5]}"
        )

    for film in films:
        record = build_film_record(film, has_creature=creature[film["id"]])
        written.append(write_record(episodes_dir, record))

    if wikidata_misses:
        log.warning("wikidata join missed %d: %s", len(wikidata_misses), wikidata_misses)
    log.info("merge: wrote %d records to %s", len(written), episodes_dir)
    return written


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_merge(Path("data/raw"), Path("data/overrides"), Path("data/episodes"))


if __name__ == "__main__":
    main()
