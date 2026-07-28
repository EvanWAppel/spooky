"""Shared HTTP client for the pipeline (TASKS D-03).

PRD §8.1: every Wikimedia request carries a descriptive User-Agent (generic
agents get blocked without notice) and requests are throttled to ~1 req/sec
(parallel fetching returns 429). CLAUDE.md: do not hide or wrap errors — an
exhausted retry raises; nothing here ever returns None.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from typing import Any

import httpx

log = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "spooky/0.1 (appelew@gmail.com)"


class HttpClient:
    """A throttled, retrying GET client.

    Retries 429s, 5xxs, and transport errors with exponential backoff; any
    other 4xx raises immediately (retrying a 404 is just slower failure).
    `sleep` and `clock` are injectable so tests never actually wait.
    """

    def __init__(
        self,
        user_agent: str | None = None,
        *,
        min_interval: float = 1.0,
        retries: int = 3,
        backoff_base: float = 1.0,
        timeout: float = 30.0,
        sleep: Callable[[float], object] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._min_interval = min_interval
        self._retries = retries
        self._backoff_base = backoff_base
        self._sleep = sleep
        self._clock = clock
        self._last_request: float | None = None
        self._client = httpx.Client(
            headers={
                "User-Agent": user_agent
                or os.getenv("WIKI_USER_AGENT", DEFAULT_USER_AGENT)
            },
            timeout=timeout,
            follow_redirects=True,
        )

    def get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        return self._request("GET", url, params=params)

    def post(self, url: str, data: dict[str, Any] | None = None) -> httpx.Response:
        return self._request("POST", url, data=data)

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(self._retries):
            last_attempt = attempt == self._retries - 1
            self._throttle()
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.TransportError:
                log.warning(
                    "%s %s: transport error (attempt %d/%d)",
                    method,
                    url,
                    attempt + 1,
                    self._retries,
                )
                if last_attempt:
                    raise
                self._backoff(attempt)
                continue

            if response.status_code == 429 or response.status_code >= 500:
                log.warning(
                    "%s %s: HTTP %d (attempt %d/%d)",
                    method,
                    url,
                    response.status_code,
                    attempt + 1,
                    self._retries,
                )
                if last_attempt:
                    response.raise_for_status()
                self._backoff(attempt)
                continue

            response.raise_for_status()
            return response

        raise AssertionError("unreachable: every retry path raises or returns")

    def _throttle(self) -> None:
        now = self._clock()
        if self._last_request is not None:
            elapsed = now - self._last_request
            if elapsed < self._min_interval:
                self._sleep(self._min_interval - elapsed)
        self._last_request = self._clock()

    def _backoff(self, attempt: int) -> None:
        self._sleep(self._backoff_base * 2**attempt)
