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
