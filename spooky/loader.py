from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_CATEGORY_LABELS = {
    "mythology": "Mythology",
    "monster-of-the-week": "Monster-of-the-Week",
    "standalone": "Standalone",
}


def load_episodes(path: Path | str) -> pd.DataFrame:
    episode_dir = Path(path)
    records = [
        json.loads(file_path.read_text(encoding="utf-8"))
        for file_path in sorted(episode_dir.glob("*.json"))
    ]
    df = pd.DataFrame.from_records(records)

    if df.empty:
        return df

    df["air_date"] = pd.to_datetime(df["air_date"], format="%Y-%m-%d")
    # Nullable Int64: films are first-class rows with no season/episode/
    # tvmaze_id (PRD §3.1), and plain int64 raises on their nulls.
    df["tvmaze_id"] = df["tvmaze_id"].astype("Int64")
    df["season"] = df["season"].astype("Int64")
    df["episode"] = df["episode"].astype("Int64")
    df["rating"] = df["rating"].astype("float64")
    df["label_contested"] = df["label_contested"].astype("bool")
    df["category"] = df["label_derived"].map(_CATEGORY_LABELS)
    df["season_episode"] = df.apply(_format_season_episode, axis=1)
    return df.sort_values(["season", "episode", "title"], kind="stable").reset_index(
        drop=True
    )


def _format_season_episode(record: pd.Series) -> str:
    season = record["season"]
    episode = record["episode"]
    if pd.isna(season) or pd.isna(episode):
        return "Film"
    return f"S{int(season):02d}E{int(episode):02d}"
