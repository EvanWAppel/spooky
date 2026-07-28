"""Step 5 — TVmaze guest cast and crew (TASKS D-11).

218 ``/guestcast`` + 218 ``/guestcrew`` calls, throttled to TVmaze's rate
limit (~20 req/10s). PRD §8.1: **budget an explicit retry pass** — a naive
sweep silently loses 10–15 episodes to transient failures. Failures are
collected, retried once as a batch, and anything still failing raises
(CLAUDE.md: do not hide or wrap errors).

Downstream reminder, enforced at merge time: crew is the **union** of
``Writer``, ``Story``, and ``Teleplay`` guestCrewTypes — filtering on
``Writer`` alone drops 11 episodes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from build._http import HttpClient

log = logging.getLogger(__name__)

EPISODE_URL = "https://api.tvmaze.com/episodes/{id}/{kind}"
KINDS = ("guestcast", "guestcrew")

# Writers hide under three guestCrewTypes; "Writer" alone drops 11 episodes.
WRITER_TYPES = frozenset({"Writer", "Story", "Teleplay"})


def _names_by_type(
    members: list[dict[str, Any]], wanted: frozenset[str] | set[str]
) -> list[str]:
    """Unique person names whose crew type is in ``wanted``, input order.

    Accepts both the raw sweep shape (``person.name``) and the distilled
    fixture shape (``name``).
    """
    names: list[str] = []
    for member in members:
        if member.get("guestCrewType") not in wanted:
            continue
        name = member.get("name") or member.get("person", {}).get("name")
        if name and name not in names:
            names.append(name)
    return names


def extract_writers(members: list[dict[str, Any]]) -> list[str]:
    """The union of Writer, Story, and Teleplay credits (PRD §8.1)."""
    return _names_by_type(members, WRITER_TYPES)


def extract_directors(members: list[dict[str, Any]]) -> list[str]:
    return _names_by_type(members, {"Director"})


def _episode_ids(raw_dir: Path) -> list[int]:
    spine = json.loads((raw_dir / "tvmaze_episodes.json").read_text())
    return [episode["id"] for episode in spine]


def _sweep(
    http: HttpClient, targets: list[tuple[int, str]]
) -> tuple[dict[str, dict[int, Any]], list[tuple[int, str]]]:
    """One pass over (episode_id, kind) targets; returns results + failures."""
    results: dict[str, dict[int, Any]] = {kind: {} for kind in KINDS}
    failures: list[tuple[int, str]] = []
    for episode_id, kind in targets:
        url = EPISODE_URL.format(id=episode_id, kind=kind)
        try:
            results[kind][episode_id] = http.get(url).json()
        except Exception:
            # Collected for the mandatory retry pass below — re-raised there
            # if the retry also fails, never swallowed.
            log.warning("failed: %s %d (queued for retry)", kind, episode_id)
            failures.append((episode_id, kind))
    return results, failures


def fetch_people(http: HttpClient, raw_dir: Path) -> dict[str, dict[int, Any]]:
    episode_ids = _episode_ids(raw_dir)
    targets = [(episode_id, kind) for episode_id in episode_ids for kind in KINDS]
    log.info("sweeping %d calls for %d episodes", len(targets), len(episode_ids))

    results, failures = _sweep(http, targets)

    if failures:
        log.info("retry pass: %d failures", len(failures))
        retried, still_failing = _sweep(http, failures)
        for kind in KINDS:
            results[kind].update(retried[kind])
        if still_failing:
            raise RuntimeError(
                f"{len(still_failing)} calls failed even after the retry pass: "
                f"{still_failing[:10]}"
            )

    for kind in KINDS:
        missing = [e for e in episode_ids if e not in results[kind]]
        if missing:
            raise RuntimeError(f"{kind}: {len(missing)} episodes missing: {missing[:10]}")
        covered = sum(1 for e in episode_ids if results[kind].get(e))
        log.info(
            "%s: %d/%d episodes covered (%d non-empty)",
            kind,
            len(results[kind]),
            len(episode_ids),
            covered,
        )
    return results


def write_raw(http: HttpClient, raw_dir: Path) -> list[Path]:
    results = fetch_people(http, raw_dir)
    written = []
    for kind in KINDS:
        out = raw_dir / f"{kind}.json"
        # JSON keys are strings; keep them as the TVmaze episode id.
        out.write_text(
            json.dumps({str(k): v for k, v in sorted(results[kind].items())}, indent=1)
            + "\n"
        )
        log.info("wrote %s (%d episodes)", out, len(results[kind]))
        written.append(out)
    return written


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # TVmaze allows ~20 req/10s; 0.5s spacing stays safely under it.
    write_raw(HttpClient(min_interval=0.5), Path("data/raw"))


if __name__ == "__main__":
    main()
