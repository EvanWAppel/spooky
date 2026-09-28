"""FTS5 full-text search over titles + loglines (Group R.1, TASKS R-01).

TDD: written before ``spooky/search.py`` exists. The index is built in memory
from a DataFrame — the same shape ``spooky.loader.load_episodes`` produces — so
no committed ``*.sqlite`` is ever a runtime dependency (CLAUDE.md: JSON is the
source of truth, SQLite is a build output).
"""

from __future__ import annotations

import pandas as pd
import pytest

from spooky.search import build_index, displayed_logline, search


def _df(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame.from_records(records)


@pytest.fixture
def index():
    records = [
        {
            "id": "s01e01",
            "title": "Pilot",
            "logline": "Agents investigate missing time near Oregon.",
            "logline_generated": "draft",
            "review_status": "human-reviewed",
        },
        {
            "id": "s04e20",
            "title": "Small Potatoes",
            "logline": "A hospital tricks families; a shapeshifter grabs a pilot's seat.",
            "logline_generated": "draft",
            "review_status": "human-reviewed",
        },
        {
            "id": "s03e15",
            "title": "Piper Maru",
            "logline": "A salvage diver surfaces changed after a wartime wreck.",
            "logline_generated": "draft",
            "review_status": "human-reviewed",
        },
    ]
    return build_index(_df(records))


def test_title_token_match(index):
    assert search(index, "piper") == ["s03e15"]


def test_logline_token_matches_body_only_term(index):
    # "oregon" appears in a logline, in no title — the win a substring-on-title
    # search could never deliver (TASKS R-03 acceptance).
    assert search(index, "oregon") == ["s01e01"]


def test_title_hit_ranks_above_body_only_hit(index):
    # Both records contain "pilot"; the title hit (s01e01) must sort first.
    results = search(index, "pilot")
    assert set(results) == {"s01e01", "s04e20"}
    assert results[0] == "s01e01"


def test_prefix_recall(index):
    # A bare term matches by prefix: "div" finds "diver".
    assert search(index, "div") == ["s03e15"]


def test_no_match_returns_empty(index):
    assert search(index, "zzzzznomatch") == []


@pytest.mark.parametrize("query", ["", "   ", "\t\n", "!!!", "()"])
def test_empty_or_tokenless_query_returns_empty(index, query):
    assert search(index, query) == []


@pytest.mark.parametrize("query", ['"', "*", "AND", "(", 'die"hand', "a AND b", "NEAR("])
def test_hostile_input_does_not_raise(index, query):
    # User text is sanitized to tokens, never passed as raw FTS5 syntax.
    result = search(index, query)
    assert isinstance(result, list)


def test_limit_caps_results(index):
    assert len(search(index, "a", limit=1)) <= 1


# --- displayed_logline: mirror components/panel._description so search indexes
#     exactly the logline text a reader sees (real corpus has logline=None). ---


def test_displayed_logline_prefers_reviewed():
    rec = {
        "logline": "reviewed text",
        "logline_generated": "draft text",
        "review_status": "human-reviewed",
    }
    assert displayed_logline(rec) == "reviewed text"


def test_displayed_logline_falls_back_to_draft_when_not_reviewed():
    rec = {
        "logline": None,
        "logline_generated": "draft text",
        "review_status": "ai-drafted",
    }
    assert displayed_logline(rec) == "draft text"


def test_displayed_logline_empty_when_both_missing():
    rec = {"logline": None, "logline_generated": None, "review_status": "ai-drafted"}
    assert displayed_logline(rec) == ""


def test_index_columns_are_only_id_title_logline(index):
    # Legal guard (R-04): the index carries no synopsis/summary column, so a
    # future change cannot make a plot recap searchable (C3). Titles and 30-word
    # loglines are the only text indexed.
    cols = [row[1] for row in index.execute("PRAGMA table_info(episodes_fts)")]
    assert cols == ["id", "title", "logline"]


def test_id_is_not_searchable(index):
    # Review finding: an id-prefix token ("s01") must not match rows by their
    # key — id is UNINDEXED, so only titles and loglines are searched.
    assert search(index, "s01") == []
    assert search(index, "s03e15") == []


def test_search_works_from_another_thread(index):
    # Review finding (high): the index is built on one thread and queried on
    # request-handler threads; check_same_thread=False + a lock must make that
    # safe rather than raising sqlite3.ProgrammingError.
    import threading

    out: dict[str, object] = {}

    def worker():
        try:
            out["result"] = search(index, "piper")
        except Exception as exc:  # noqa: BLE001 — record any error to assert on
            out["error"] = exc

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert "error" not in out, out.get("error")
    assert out["result"] == ["s03e15"]


def test_ai_drafted_records_are_searchable_via_their_draft():
    # The real corpus: logline is null, the AI draft carries the words.
    df = _df(
        [
            {
                "id": "s05e01",
                "title": "Redux",
                "logline": None,
                "logline_generated": "A cure in the Pentagon undoes a faked death.",
                "review_status": "ai-drafted",
            }
        ]
    )
    assert search(build_index(df), "pentagon") == ["s05e01"]
