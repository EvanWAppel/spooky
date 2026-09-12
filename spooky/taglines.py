"""Opening-title-sequence taglines — the shared domain layer (PRD §7, v2).

The X-Files title sequence always ends on a card reading **"The Truth Is Out
There."** In a documented minority of episodes it is swapped for an
episode-specific line — "Trust No One", "Apology is Policy", the Navajo line in
"Anasazi", and so on. Which episodes get one, and what it says, is a fandom
detail this project surfaces *as data* (never as imagery — the tagline ships as
plain site text only; PRD §11.1, constraint C2).

This module holds only what both the data layer (``spooky/loader.py``,
``components/panel.py``) and the build step (``build/taglines.py``) need: the
series default and the derivation of "is this a variant?". The build-only
concerns — the curated override, the prose scanner, the drift check — live in
``build/taglines.py`` so the app layer never imports the pipeline.
"""

from __future__ import annotations

import re
from typing import Any

from spooky.values import is_missing

# The series default, as it appears in the title card. A constant, not a count —
# it never shifts, so hard-coding it here is a fact, not a hard-coded metric.
DEFAULT_TAGLINE = "The Truth Is Out There"


def normalize(text: str | None) -> str:
    """Collapse a tagline to comparable form: lowercase, alphanumerics only.

    So "The truth is out there", "The Truth Is Out There", and
    "The Truth is Out There." all compare equal — Wikipedia's prose is
    inconsistent about the casing of the default.
    """
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def is_variant(text: str | None) -> bool:
    """True when ``text`` is a real deviation from the series default."""
    normalized = normalize(text)
    return bool(normalized) and normalized != normalize(DEFAULT_TAGLINE)


def text_of(record: dict[str, Any]) -> str:
    """The tagline for a record, reading either the flattened column or the
    nested ``tagline`` object, defaulting to the series line.

    Records reach the panel two ways — as a raw dict (the nested ``tagline``
    object from ``data/episodes``) and as a DataFrame row (the flattened
    ``tagline_text`` column the loader adds). Handle both, and treat a missing
    value as the default rather than blank.
    """
    flat = record.get("tagline_text")
    if not is_missing(flat) and flat:
        return str(flat)
    nested = record.get("tagline")
    if isinstance(nested, dict) and nested.get("text"):
        return str(nested["text"])
    return DEFAULT_TAGLINE


def is_variant_of(record: dict[str, Any]) -> bool:
    """Whether a record carries a variant tagline (flattened or nested)."""
    flat = record.get("tagline_is_variant")
    if not is_missing(flat):
        return bool(flat)
    nested = record.get("tagline")
    if isinstance(nested, dict) and "is_variant" in nested:
        return bool(nested["is_variant"])
    return is_variant(text_of(record))


def note_of(record: dict[str, Any]) -> str | None:
    """The owner/AI gloss on why the tagline changed, if any (nested only).

    The gloss lifecycle (draft → review) is deferred alongside the logline
    review pass, so this is ``None`` until that work lands (PRD §7 tasks
    T-06/T-07). The panel renders it when present and simply omits it otherwise.
    """
    nested = record.get("tagline")
    if not isinstance(nested, dict):
        return None
    for field in ("note", "note_generated"):
        value = nested.get(field)
        if value and not is_missing(value):
            return str(value)
    return None
