from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "id",
    "tvmaze_id",
    "season",
    "episode",
    "season_episode",
    "title",
    "air_date",
    "production_code",
    "runtime",
    "rating",
    "label_fox_dvd",
    "label_wikipedia",
    "label_dom111",
    "label_derived",
    "category",
    "label_contested",
    "label_rationale",
    "imdb_id",
    "tmdb_id",
    "tmdb_movie_id",
    "director",
    "writers",
    "guest_cast",
    "logline_generated",
    "logline",
    "review_status",
    "reviewed_at",
    "review_note",
    "provenance",
}


def test_load_episodes_returns_dataframe_with_full_column_set(
    episodes_df: pd.DataFrame,
) -> None:
    assert isinstance(episodes_df, pd.DataFrame)
    assert len(episodes_df) == 12
    assert REQUIRED_COLUMNS.issubset(episodes_df.columns)


def test_load_real_dataset_including_films() -> None:
    """The real corpus has 2 film records with null season/episode/tvmaze_id.

    ``astype("int64")`` crashes on those — the loader must use pandas'
    nullable Int64 so films are first-class rows (PRD §3.1).
    """
    from pathlib import Path

    from spooky.loader import load_episodes

    df = load_episodes(Path(__file__).resolve().parent.parent / "data" / "episodes")

    films = df[df["season"].isna()]
    episodes = df[df["season"].notna()]
    assert len(df) == len(episodes) + len(films)
    assert len(films) == 2
    assert set(films["season_episode"]) == {"Film"}
    assert films["title"].str.startswith("The X-Files").all()
    # Episode rows keep integer dtypes despite the nullable columns.
    assert pd.api.types.is_integer_dtype(df["season"])
    assert pd.api.types.is_integer_dtype(df["episode"])


def test_load_episodes_sets_expected_dtypes(episodes_df: pd.DataFrame) -> None:
    assert pd.api.types.is_integer_dtype(episodes_df["tvmaze_id"])
    assert pd.api.types.is_integer_dtype(episodes_df["season"])
    assert pd.api.types.is_integer_dtype(episodes_df["episode"])
    assert pd.api.types.is_float_dtype(episodes_df["rating"])
    assert pd.api.types.is_bool_dtype(episodes_df["label_contested"])
    assert pd.api.types.is_datetime64_any_dtype(episodes_df["air_date"])
    assert episodes_df["director"].map(type).eq(list).all()
    assert episodes_df["writers"].map(type).eq(list).all()
    assert episodes_df["guest_cast"].map(type).eq(list).all()
