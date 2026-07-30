"""The processed episode table's contract.

Every analysis in notebooks/ reads data/processed/episodes.parquet and assumes
things about it that are never stated in code: that it holds a particular
population, that the ordering column is dense, that the rating columns are
inside IMDb's own range. These are the assumptions -- if a filter in
src/build.py changes, this file is what notices.

Run from the repository root:  pytest
"""

import pandas as pd
import pytest

# The population reported everywhere: README, the essay, the technical report,
# and every percentage derived from them.
N_EPISODES = 192_720
N_SHOWS = 3_234

REQUIRED_COLUMNS = [
    "episode_tconst", "show_tconst", "show_title", "genres",
    "start_year", "end_year", "ongoing",
    "season_number", "episode_number", "overall_order",
    "average_rating", "num_votes",
]


@pytest.fixture(scope="module")
def episodes():
    return pd.read_parquet("data/processed/episodes.parquet")


def test_population_matches_the_reported_figures(episodes):
    assert len(episodes) == N_EPISODES
    assert episodes["show_tconst"].nunique() == N_SHOWS


def test_required_columns_are_present(episodes):
    assert list(episodes.columns) == REQUIRED_COLUMNS


def test_columns_the_analysis_indexes_on_are_never_null(episodes):
    # start_year/end_year are allowed to be null (end_year null IS the ongoing
    # flag); nothing else may be, or a groupby silently drops rows.
    for column in ["show_tconst", "season_number", "episode_number",
                   "overall_order", "average_rating", "num_votes", "ongoing"]:
        assert episodes[column].notna().all(), f"{column} has nulls"


def test_ratings_and_votes_sit_inside_imdb_ranges(episodes):
    assert episodes["average_rating"].between(1.0, 10.0).all()
    assert (episodes["num_votes"] >= 1).all()


def test_overall_order_is_dense_and_one_based_within_each_show(episodes):
    """Every trajectory fit maps overall_order onto a 0-1 axis with
    (order - 1) / (n - 1), which is only a correct normalisation if the column
    runs 1..n with no gaps and no repeats inside each show."""
    grouped = episodes.groupby("show_tconst")["overall_order"]
    assert (grouped.min() == 1).all()
    assert (grouped.max() == grouped.count()).all()
    assert (grouped.nunique() == grouped.count()).all()


def test_overall_order_follows_season_then_episode(episodes):
    """The ordering must be chronological within a show, otherwise a 'trend
    across the run' is a trend across an arbitrary permutation."""
    ordered = episodes.sort_values(["show_tconst", "overall_order"])
    keys = ordered.groupby("show_tconst")[["season_number", "episode_number"]]
    assert keys.apply(lambda g: g.apply(tuple, axis=1).is_monotonic_increasing).all()


def test_inclusion_filters_actually_held(episodes):
    """The six rules from docs/decisions.md, checked on the output rather than
    trusted from the build log."""
    per_show = episodes.groupby("show_tconst").agg(
        episode_count=("episode_tconst", "count"),
        season_count=("season_number", "nunique"),
        mean_votes=("num_votes", "mean"),
        genres=("genres", "first"),
    )
    assert (per_show["episode_count"] >= 13).all()
    assert (per_show["season_count"] >= 2).all()
    assert (per_show["mean_votes"] >= 50).all()

    excluded = {"Game-Show", "Reality-TV", "Talk-Show", "News"}
    genre_sets = per_show["genres"].fillna("").str.split(",").apply(set)
    assert not genre_sets.apply(lambda gs: bool(gs & excluded)).any()

    documentaries = per_show[genre_sets.apply(lambda gs: "Documentary" in gs)]
    assert (documentaries["episode_count"] < 100).all()


def test_ongoing_flag_agrees_with_missing_end_year(episodes):
    assert (episodes["ongoing"] == episodes["end_year"].isna()).all()
