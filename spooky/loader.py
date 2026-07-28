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
    df["tvmaze_id"] = df["tvmaze_id"].astype("int64")
    df["season"] = df["season"].astype("int64")
    df["episode"] = df["episode"].astype("int64")
    df["rating"] = df["rating"].astype("float64")
    df["label_contested"] = df["label_contested"].astype("bool")
    df["category"] = df["label_derived"].map(_CATEGORY_LABELS)
    df["season_episode"] = df.apply(_format_season_episode, axis=1)
    return df.sort_values(["season", "episode", "title"], kind="stable").reset_index(
        drop=True
    )


def _format_season_episode(record: pd.Series) -> str:
    season = int(record["season"])
    episode = int(record["episode"])
    return f"S{season:02d}E{episode:02d}"
