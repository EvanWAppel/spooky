"""Shared pytest fixtures.

CLAUDE.md: *use pytest fixtures in conftest.py to DRY.*

Paths are anchored to the repository root rather than the current working
directory so the suite passes regardless of where pytest is invoked from.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from dash.development.base_component import Component

from spooky.loader import load_episodes

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


# --- pipeline fixtures (recorded real payloads — see tests/fixtures/README.md) ---


@pytest.fixture(scope="session")
def tvmaze_payload() -> list[dict[str, Any]]:
    """The full recorded TVmaze episodes payload (218 records)."""
    import json

    return json.loads((FIXTURES_DIR / "tvmaze_episodes.json").read_text())


@pytest.fixture
def sample_tvmaze_episode(tvmaze_payload: list[dict[str, Any]]) -> dict[str, Any]:
    """One real TVmaze episode record (the pilot)."""
    return dict(tvmaze_payload[0])


@pytest.fixture(scope="session")
def sample_wiki_season_wikitext() -> dict[int, str]:
    """Recorded Wikipedia wikitext keyed by season (the parser edge cases)."""
    return {
        season: (FIXTURES_DIR / f"wiki_s{season:02d}.txt").read_text()
        for season in (3, 10, 11)
    }


@pytest.fixture
def sample_wikidata_row() -> dict[str, Any]:
    """Shape of one Wikidata SPARQL result row (refined at D-08)."""
    return {
        "qid": "Q2342086",
        "enwiki_title": "Pilot (The X-Files)",
        "imdb_id": "tt0751141",
        "tmdb_id": 4087,
    }


@pytest.fixture
def sample_dom111_record() -> dict[str, Any]:
    """Shape of one dom111/xfiles-episode-picker record (refined at D-09)."""
    return {"title": "Squeeze", "season": 1, "episode": 3, "type": "motw"}


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """A throwaway data/ layout for pipeline write tests."""
    for sub in ("raw", "episodes", "overrides", "dist"):
        (tmp_path / sub).mkdir()
    return tmp_path


# --- app-layer fixtures ---


@pytest.fixture(scope="session")
def sample_data_dir() -> Path:
    """The 12 hand-built vertical-slice sample records."""
    return REPO_ROOT / "data" / "episodes_sample"


@pytest.fixture(scope="session")
def _episodes_df_cached(sample_data_dir: Path) -> pd.DataFrame:
    """Load the sample records once per session. Do not use directly."""
    return load_episodes(sample_data_dir)


@pytest.fixture
def episodes_df(_episodes_df_cached: pd.DataFrame) -> pd.DataFrame:
    """Sample records as a DataFrame.

    Returns a fresh copy per test so a test that mutates the frame cannot
    leak into another.
    """
    return _episodes_df_cached.copy(deep=True)


@pytest.fixture
def contested_record(episodes_df: pd.DataFrame) -> dict[str, Any]:
    """The first record whose three source labels disagree."""
    contested = episodes_df[episodes_df["label_contested"]]
    if contested.empty:
        raise AssertionError(
            f"No contested record in {len(episodes_df)} sample records; "
            "tests covering the contested badge and per-source breakdown "
            "cannot run."
        )
    return contested.iloc[0].to_dict()


@pytest.fixture
def render_text() -> Any:
    """Flatten a Dash component tree to a searchable string.

    Includes `href` values so out-links can be asserted on.
    """

    def _flatten(component: Any) -> str:
        if component is None:
            return ""
        if isinstance(component, str):
            return component
        if isinstance(component, (int, float, bool)):
            return str(component)
        if isinstance(component, list | tuple):
            return " ".join(_flatten(child) for child in component)
        if isinstance(component, Component):
            children = getattr(component, "children", None)
            props = []
            href = getattr(component, "href", None)
            if href:
                props.append(href)
            return " ".join([_flatten(children), *props])
        return str(component)

    return _flatten
