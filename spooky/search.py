"""In-memory FTS5 full-text search over titles + loglines (Group R.1).

The app never ships a committed database — ``*.sqlite`` is gitignored and is a
build output, not the source of truth (CLAUDE.md). This module builds the same
``fts5(id, title, logline)`` index ``build/emit.py`` writes, but in memory from
the loaded records, so search is driven entirely by ``data/episodes/*.json``.

User input is tokenized to alphanumeric prefix terms before it reaches FTS5, so
raw query syntax (quotes, ``*``, ``AND``, ``NEAR(``) can never raise a
``sqlite3.OperationalError`` — the query is data, not FTS grammar.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import threading
from typing import Any

import pandas as pd

from spooky.values import is_missing

log = logging.getLogger(__name__)

# id is UNINDEXED (stored, not searchable) so a query token that prefixes an id
# — "s01" — cannot match rows by their key; only title + logline are searched.
# title is weighted above logline so a title hit sorts before a body-only hit.
# bm25 is ascending: lower == more relevant.
_BM25_WEIGHTS = (10.0, 1.0)

# The in-memory connection is shared across request threads (check_same_thread
# is off in build_index), so every query is serialized behind this lock — the
# index is read-only after build and tiny, so contention is negligible.
_LOCK = threading.Lock()

_TOKEN = re.compile(r"[0-9A-Za-z]+")


def displayed_logline(record: Any) -> str:
    """The logline text a reader actually sees — mirrors
    ``components/panel._description``.

    A human-reviewed logline wins; otherwise the AI draft; otherwise empty. The
    real corpus has ``logline`` null and the words in ``logline_generated``, so
    indexing only ``logline`` would search nothing.
    """
    logline = record.get("logline")
    draft = record.get("logline_generated")
    if record.get("review_status") == "human-reviewed" and not is_missing(logline):
        return str(logline)
    if not is_missing(draft):
        return str(draft)
    return ""


def build_index(df: pd.DataFrame) -> sqlite3.Connection:
    """Build an in-memory FTS5 index from a loaded episodes DataFrame."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute(
        "CREATE VIRTUAL TABLE episodes_fts USING fts5(id UNINDEXED, title, logline)"
    )
    rows = [
        (
            str(record["id"]),
            "" if is_missing(record.get("title")) else str(record["title"]),
            displayed_logline(record),
        )
        for record in df.to_dict("records")
    ]
    conn.executemany(
        "INSERT INTO episodes_fts (id, title, logline) VALUES (?, ?, ?)", rows
    )
    conn.commit()
    log.info("built in-memory FTS5 index over %d records", len(rows))
    return conn


def _match_query(query: str) -> str | None:
    """Turn free user text into a safe FTS5 MATCH expression, or None.

    Each alphanumeric token becomes a prefix term (``gov`` → ``gov*``); tokens
    are space-joined (FTS5 implicit AND). Punctuation and operator words carry
    no special meaning — they are just tokens or dropped.
    """
    tokens = _TOKEN.findall(query or "")
    if not tokens:
        return None
    # Quote each token so an FTS5 keyword (AND/OR/NOT/NEAR) is treated as a
    # string literal, not an operator; the trailing * makes it a prefix term.
    # Tokens are alphanumeric-only, so there is nothing inside to escape.
    return " ".join(f'"{token}"*' for token in tokens)


def search(conn: sqlite3.Connection, query: str, limit: int | None = None) -> list[str]:
    """Return record ids matching ``query``, most relevant first."""
    match = _match_query(query)
    if match is None:
        return []
    sql = (
        "SELECT id FROM episodes_fts WHERE episodes_fts MATCH ? "
        "ORDER BY bm25(episodes_fts, ?, ?)"
    )
    params: list[Any] = [match, *_BM25_WEIGHTS]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with _LOCK:
        ids = [row[0] for row in conn.execute(sql, params)]
    log.info("search %r → %d hits", query, len(ids))
    return ids
