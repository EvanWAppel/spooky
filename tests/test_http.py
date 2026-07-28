"""Tests for the shared pipeline HTTP client (TASKS D-03).

CLAUDE.md: do not hide or wrap errors — an exhausted retry raises, never
returns None. PRD §8.1: Wikimedia requests need a descriptive User-Agent and
~1 req/sec throttling.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from build._http import HttpClient

URL = "https://example.test/resource"


def _no_sleep_client(**kwargs) -> tuple[HttpClient, list[float]]:
    """An HttpClient whose sleeps are recorded instead of slept."""
    slept: list[float] = []
    client = HttpClient(
        user_agent="spooky-test/0.1 (test@example.test)",
        sleep=slept.append,
        **kwargs,
    )
    return client, slept


@respx.mock
def test_sends_descriptive_user_agent() -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={}))
    client, _ = _no_sleep_client()

    client.get(URL)

    request = route.calls.last.request
    assert request.headers["User-Agent"] == "spooky-test/0.1 (test@example.test)"


@respx.mock
def test_retries_through_429_then_succeeds() -> None:
    route = respx.get(URL).mock(
        side_effect=[
            httpx.Response(429),
            httpx.Response(429),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    # min_interval=0 so the recorded waits are backoff alone, not throttle.
    client, slept = _no_sleep_client(retries=3, min_interval=0.0)

    response = client.get(URL)

    assert response.json() == {"ok": True}
    assert route.call_count == 3
    # Backoff actually waited (recorded, not slept) and grew between attempts.
    waits = [s for s in slept if s > 0]
    assert len(waits) == 2
    assert waits[1] > waits[0]


@respx.mock
def test_exhausted_retries_raise_instead_of_returning_none() -> None:
    respx.get(URL).mock(return_value=httpx.Response(429))
    client, _ = _no_sleep_client(retries=2)

    with pytest.raises(httpx.HTTPStatusError):
        client.get(URL)


@respx.mock
def test_client_errors_other_than_429_do_not_retry() -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(404))
    client, _ = _no_sleep_client(retries=3)

    with pytest.raises(httpx.HTTPStatusError):
        client.get(URL)

    assert route.call_count == 1


@respx.mock
def test_consecutive_requests_are_throttled() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, json={}))
    clock = iter([0.0, 0.05, 0.1, 0.15, 0.2, 0.25]).__next__
    client, slept = _no_sleep_client(min_interval=1.0, clock=clock)

    client.get(URL)
    client.get(URL)

    # The second call had to wait out the remainder of the 1s interval.
    assert any(s >= 0.5 for s in slept)
