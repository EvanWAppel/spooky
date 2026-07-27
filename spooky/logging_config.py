"""Logging setup for local tools and the Dash app."""

from __future__ import annotations

import logging


def setup_logging(level: str | int = "INFO") -> None:
    """Configure stdlib logging with a compact, AI-debuggable format."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
