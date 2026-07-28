"""Seed data/overrides/creature.json (TASKS E-02; PRD §5.3 rule 5).

``has_creature`` — "features a non-recurring paranormal antagonist" — is not
derivable from any source. This tool AI-seeds it and marks every entry
``source: "ai-seeded"`` so the owner can review and flip entries (review
promotes an entry to ``source: "human-reviewed"``).

Seeding heuristic:
- dom111 says ``motw``  -> has_creature True, EXCEPT the explicit
  NO_CREATURE list below — episodes whose antagonist is human, absent, or
  technological (comedy, biography, and thriller episodes).
- dom111 says ``mythology`` -> False. (The flag is unused when a mythology
  majority exists — rule 4 fires first — but every record carries one.)
- Films: from data/overrides/films.json; both False. I Want to Believe's
  antagonists are human organ traffickers — a medical-horror thriller, not
  a creature feature — which lands it "standalone" under rule 5.

Entries are keyed by title matched against the TVmaze spine (normalized), so
a typo here fails loudly instead of silently seeding nothing.

    uv run python tools/seed_creature.py
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

log = logging.getLogger(__name__)

# AI-seeded judgment calls: dom111-motw episodes with NO non-recurring
# paranormal antagonist. Every one is flagged for owner review.
NO_CREATURE: dict[str, str] = {
    "Jose Chung's From Outer Space": "unreliable-narration comedy; no antagonist",
    "The Field Where I Died": "cult standoff; antagonist is human",
    "Musings of a Cigarette Smoking Man": "CSM biography; no antagonist",
    "Unusual Suspects": "Lone Gunmen origin story; no antagonist",
    "The Pine Bluff Variant": "bioterrorism thriller; antagonists are human",
    "Triangle": "time-slip phenomenon; antagonists are human Nazis",
    "Dreamland (1)": "body-swap comedy; Morris Fletcher is human",
    "Dreamland (2)": "body-swap comedy; Morris Fletcher is human",
    "The Unnatural": "sympathetic alien ballplayer; no antagonist",
    "Three of a Kind": "Lone Gunmen caper; antagonists are human",
    "The Goldberg Variation": "luck phenomenon; antagonists are human mobsters",
    "All Things": "spiritual character study; no antagonist",
    "Improbable": "numerology comedy; God is not an antagonist",
    "Sunshine Days": "sympathetic telekinetic; no real antagonist",
    "Founder's Mutation": "human experimenter; the children are victims",
    "Babylon": "terrorism drama; antagonists are human",
    "The Lost Art of Forehead Sweat": "Mandela-effect comedy; no antagonist",
    "Rm9sbG93ZXJz": "AI antagonist — technological, not paranormal",
}


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.lower())


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    raw = REPO_ROOT / "data" / "raw"
    spine = json.loads((raw / "tvmaze_episodes.json").read_text())
    dom111 = {
        record["id"]: record["episode_type"]
        for record in json.loads((raw / "dom111.json").read_text())
    }
    films = json.loads((REPO_ROOT / "data" / "overrides" / "films.json").read_text())

    no_creature = {_norm(title): title for title in NO_CREATURE}
    matched: set[str] = set()
    entries = []
    for episode in spine:
        label = dom111[episode["id"]]
        key = _norm(episode["name"])
        if key in no_creature:
            matched.add(key)
            has_creature = False
            note = NO_CREATURE[no_creature[key]]
        else:
            has_creature = label == "motw"
            note = f"defaulted from dom111 label {label!r}"
        entries.append(
            {
                "id": f"s{episode['season']:02d}e{episode['number']:02d}",
                "title": episode["name"],
                "has_creature": has_creature,
                "source": "ai-seeded",
                "note": note,
            }
        )

    unmatched = sorted(set(no_creature) - matched)
    if unmatched:
        raise SystemExit(
            f"NO_CREATURE titles not found in the spine (typo?): "
            f"{[no_creature[k] for k in unmatched]}"
        )

    for film in films:
        entries.append(
            {
                "id": film["id"],
                "title": film["title"],
                "has_creature": False,
                "source": "ai-seeded",
                "note": "film; antagonists are human",
            }
        )

    out = REPO_ROOT / "data" / "overrides" / "creature.json"
    out.write_text(json.dumps(entries, indent=1) + "\n")
    flagged = sum(1 for entry in entries if not entry["has_creature"])
    log.info(
        "wrote %s: %d entries, %d without creature (%d explicit calls)",
        out,
        len(entries),
        flagged,
        len(NO_CREATURE),
    )


if __name__ == "__main__":
    main()
