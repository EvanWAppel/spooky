"""Vote-based episode classification (PRD §5.3; TASKS E-01).

**A null source label abstains** — it is neither a yes nor a no (DECISIONS.md
OPEN-01). The Fox DVD sets predate the revival, and no episode source covers
the films, so nulls are the norm at the corpus edges, not an error state.

Rules, in order:

1. Votes are the non-null source labels; ``not-listed``/``not-flagged``/
   ``motw`` are negative votes, not abstentions.
2. Contested whenever the votes disagree or fewer than three sources voted.
3. Zero votes raises — classification then belongs in
   ``data/overrides/classification.json``, hand-ruled with a rationale.
4. A strict majority of mythology votes → ``mythology``.
5. Otherwise ``has_creature`` decides monster-of-the-week vs standalone.
"""

from __future__ import annotations

MYTHOLOGY = "mythology"
MOTW = "monster-of-the-week"
STANDALONE = "standalone"

_ALLOWED = {
    "fox": {MYTHOLOGY, "not-listed", None},
    "wiki": {MYTHOLOGY, "not-flagged", None},
    "dom111": {MYTHOLOGY, "motw", None},
}
_SOURCE_NAMES = {"fox": "Fox DVDs", "wiki": "Wikipedia", "dom111": "dom111"}


def derive_label(
    *,
    fox: str | None,
    wiki: str | None,
    dom111: str | None,
    has_creature: bool,
) -> tuple[str, bool, str]:
    """Return ``(label_derived, label_contested, label_rationale)``."""
    values = {"fox": fox, "wiki": wiki, "dom111": dom111}
    for source, value in values.items():
        if value not in _ALLOWED[source]:
            raise ValueError(
                f"unknown {_SOURCE_NAMES[source]} label {value!r}; "
                f"expected one of {sorted(v for v in _ALLOWED[source] if v)}"
            )

    votes = {source: value for source, value in values.items() if value is not None}
    abstaining = [_SOURCE_NAMES[s] for s in values if s not in votes]

    if not votes:
        raise ValueError(
            "no source covers this record — add a hand-ruled entry with a "
            "rationale to data/overrides/classification.json"
        )

    mythology_votes = [s for s, v in votes.items() if v == MYTHOLOGY]
    disagree = 0 < len(mythology_votes) < len(votes)
    contested = disagree or len(votes) < 3

    abstain_note = (
        f" {', '.join(abstaining)} do not cover this record and abstain."
        if abstaining
        else ""
    )

    if len(mythology_votes) * 2 > len(votes):
        rationale = (
            f"{len(mythology_votes)} of {len(votes)} voting sources say "
            f"mythology.{abstain_note}"
        )
        return MYTHOLOGY, contested, rationale

    creature_note = (
        "features a non-recurring paranormal antagonist"
        if has_creature
        else "features no non-recurring paranormal antagonist"
    )
    label = MOTW if has_creature else STANDALONE
    rationale = (
        f"{len(mythology_votes)} of {len(votes)} voting sources say mythology; "
        f"{creature_note}.{abstain_note}"
    )
    return label, contested, rationale
