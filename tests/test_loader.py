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
    "tagline_text",
    "tagline_is_variant",
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


def test_loader_defaults_tagline_columns_when_absent(
    episodes_df: pd.DataFrame,
) -> None:
    """The hand-built sample records carry no ``tagline`` object; the loader
    must surface the series default rather than a null (T-01)."""
    from spooky.taglines import DEFAULT_TAGLINE

    assert (episodes_df["tagline_text"] == DEFAULT_TAGLINE).all()
    assert episodes_df["tagline_is_variant"].eq(False).all()
    assert pd.api.types.is_bool_dtype(episodes_df["tagline_is_variant"])


def test_loader_surfaces_tagline_variants_from_the_real_corpus() -> None:
    """The real records carry tagline objects; a known variant flattens through,
    and the variant count re-derives to the committed override's length."""
    import json
    from pathlib import Path

    from spooky.loader import load_episodes

    root = Path(__file__).resolve().parent.parent
    df = load_episodes(root / "data" / "episodes")

    apology = df[df["id"] == "s03e10"].iloc[0]
    assert apology["tagline_text"] == "Apology is Policy"
    assert bool(apology["tagline_is_variant"]) is True

    override_path = root / "data" / "overrides" / "taglines.json"
    expected = len(json.loads(override_path.read_text()))
    assert int(df["tagline_is_variant"].sum()) == expected


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
