"""Tests for the Films card (TASKS G-03).

Films are first-class records excluded from the season chart (PRD §3.1);
they surface in their own card with their own watch links.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from components.films import build_films_card
from spooky.loader import load_episodes

EPISODES_DIR = Path(__file__).resolve().parent.parent / "data" / "episodes"


@pytest.fixture(scope="module")
def real_df():
    return load_episodes(EPISODES_DIR)


def test_films_card_renders_both_films_with_links(
    real_df, render_text: Callable[[Any], str]
) -> None:
    card = build_films_card(real_df)
    rendered = render_text(card)

    assert "Fight the Future" in rendered
    assert "I Want to Believe" in rendered
    # Film watch links go to the TMDB movie page, not a season page.
    assert "https://www.themoviedb.org/movie/846-the-x-files/watch" in rendered
    assert "https://www.themoviedb.org/movie/8836-the-x-files/watch" in rendered
    assert "https://www.imdb.com/title/tt0120902/" in rendered


def test_films_card_shows_categories_and_contested_state(
    real_df, render_text: Callable[[Any], str]
) -> None:
    rendered = render_text(build_films_card(real_df))

    # FTF derives mythology from its single Wikipedia vote; IWTB standalone.
    assert "Mythology" in rendered
    assert "Standalone" in rendered
    assert "Contested" in rendered


def test_films_card_with_no_films_renders_nothing(real_df) -> None:
    episodes_only = real_df[real_df["season"].notna()]

    assert build_films_card(episodes_only) is None
