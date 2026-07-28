"""Tests for the vote-based classification rules (TASKS B-09, E-01; PRD §5.3).

Null = abstain (DECISIONS.md OPEN-01): a source that does not cover a record
is neither a yes nor a no. Fewer than three votes always marks the record
contested; zero votes is a build error, never a silent default.
"""

from __future__ import annotations

import pytest

from spooky.classify import derive_label


def test_unanimous_three_vote_mythology_is_uncontested() -> None:
    label, contested, rationale = derive_label(
        fox="mythology", wiki="mythology", dom111="mythology", has_creature=False
    )

    assert label == "mythology"
    assert contested is False
    assert rationale


def test_unanimous_non_mythology_with_creature_is_motw() -> None:
    label, contested, _ = derive_label(
        fox="not-listed", wiki="not-flagged", dom111="motw", has_creature=True
    )

    assert label == "monster-of-the-week"
    assert contested is False


def test_unanimous_non_mythology_without_creature_is_standalone() -> None:
    label, contested, _ = derive_label(
        fox="not-listed", wiki="not-flagged", dom111="motw", has_creature=False
    )

    assert label == "standalone"
    assert contested is False


def test_two_one_mythology_majority_is_mythology_and_contested() -> None:
    label, contested, rationale = derive_label(
        fox="not-listed", wiki="mythology", dom111="mythology", has_creature=False
    )

    assert label == "mythology"
    assert contested is True
    assert "2" in rationale


def test_lone_mythology_minority_falls_to_creature_rule() -> None:
    """Under the old rules a lone mythology vote forced MOTW; now the
    has_creature flag decides — that is what the flag is for."""
    motw, contested_a, _ = derive_label(
        fox="mythology", wiki="not-flagged", dom111="motw", has_creature=True
    )
    standalone, contested_b, _ = derive_label(
        fox="mythology", wiki="not-flagged", dom111="motw", has_creature=False
    )

    assert motw == "monster-of-the-week"
    assert standalone == "standalone"
    assert contested_a is True and contested_b is True


def test_two_vote_revival_records_are_always_contested() -> None:
    """The Fox DVDs predate the revival — every S10/S11 record has 2 votes."""
    label, contested, rationale = derive_label(
        fox=None, wiki="mythology", dom111="mythology", has_creature=False
    )

    assert label == "mythology"
    assert contested is True
    assert "2" in rationale


def test_single_wikipedia_vote_classifies_fight_the_future() -> None:
    """Films carry exactly one vote — Wikipedia's dagger (PRD §8.1 step 07)."""
    label, contested, _ = derive_label(
        fox=None, wiki="mythology", dom111=None, has_creature=False
    )

    assert label == "mythology"
    assert contested is True


def test_one_one_tie_falls_to_creature_rule_and_is_contested() -> None:
    label, contested, _ = derive_label(
        fox=None, wiki="mythology", dom111="motw", has_creature=True
    )

    assert label == "monster-of-the-week"
    assert contested is True


def test_zero_votes_raises_instead_of_defaulting() -> None:
    with pytest.raises(ValueError, match="classification.json"):
        derive_label(fox=None, wiki=None, dom111=None, has_creature=False)


@pytest.mark.parametrize(
    ("kwargs", "bad"),
    [
        ({"fox": "maybe", "wiki": "mythology", "dom111": "motw"}, "maybe"),
        ({"fox": None, "wiki": "dagger", "dom111": "motw"}, "dagger"),
        ({"fox": None, "wiki": "mythology", "dom111": "standalone"}, "standalone"),
    ],
)
def test_unknown_label_values_raise(kwargs: dict, bad: str) -> None:
    """Do not hide errors: an unrecognized source value is a bug upstream."""
    with pytest.raises(ValueError, match=bad):
        derive_label(has_creature=False, **kwargs)


def test_rationale_explains_abstentions() -> None:
    _, _, rationale = derive_label(
        fox=None, wiki="mythology", dom111=None, has_creature=False
    )

    assert "abstain" in rationale.lower() or "not cover" in rationale.lower()
