"""Tests for the TVmaze spine fetch (TASKS B-04, B-05, D-01, D-02)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from build._http import HttpClient
from build.spine import TVMAZE_EPISODES_URL, fetch_episodes, write_raw


@pytest.fixture
def http() -> HttpClient:
    return HttpClient(user_agent="spooky-test/0.1", sleep=lambda _s: None)


@respx.mock
def test_fetch_episodes_returns_all_records_with_expected_keys(
    tvmaze_payload: list[dict[str, Any]], http: HttpClient
) -> None:
    respx.get(TVMAZE_EPISODES_URL).mock(
        return_value=httpx.Response(200, json=tvmaze_payload)
    )

    episodes = fetch_episodes(http)

    assert len(episodes) == 218
    for episode in episodes:
        assert {"id", "season", "number", "airdate", "rating"} <= episode.keys()


@respx.mock
def test_fetch_episodes_never_requests_specials(
    tvmaze_payload: list[dict[str, Any]], http: HttpClient
) -> None:
    """PRD §8.1: ?specials=1 returns 222 records and silently breaks the count."""
    route = respx.get(TVMAZE_EPISODES_URL).mock(
        return_value=httpx.Response(200, json=tvmaze_payload)
    )

    fetch_episodes(http)

    assert "specials" not in route.calls.last.request.url.params


@respx.mock
def test_write_raw_writes_the_payload_verbatim(
    tvmaze_payload: list[dict[str, Any]], http: HttpClient, tmp_data_dir
) -> None:
    respx.get(TVMAZE_EPISODES_URL).mock(
        return_value=httpx.Response(200, json=tvmaze_payload)
    )

    out = write_raw(http, tmp_data_dir / "raw")

    written = json.loads(out.read_text())
    assert len(written) == len(tvmaze_payload)
    assert written[0]["id"] == tvmaze_payload[0]["id"]


@pytest.mark.network
def test_live_tvmaze_returns_218_episodes() -> None:
    """D-02: the real endpoint still returns 218 (no specials)."""
    episodes = fetch_episodes(HttpClient())

    assert len(episodes) == 218
