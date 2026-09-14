"""The SQL build reproduces the pandas build, row for row.

sql/build_episodes.sql re-implements src/build.py in SQLite. This checks that
its `episodes` table holds exactly the rows and values of
data/processed/episodes.parquet -- not just the same counts.

It needs data/imdb.sqlite, which is built locally from the raw IMDb dumps
(python sql/load_raw.py, then python sql/run_build.py) and is never committed.
Where that database is absent, as on the CI runner, the tests are skipped
rather than passed.

Run from the repository root:  pytest
"""

import os
import sqlite3

import pandas as pd
import pytest

DB_PATH = "data/imdb.sqlite"

pytestmark = pytest.mark.skipif(
    not os.path.exists(DB_PATH),
    reason=f"{DB_PATH} not built (needs the raw IMDb dumps; see sql/load_raw.py)",
)


@pytest.fixture(scope="module")
def both_tables():
    parquet = pd.read_parquet("data/processed/episodes.parquet")
    with sqlite3.connect(DB_PATH) as conn:
        sql = pd.read_sql("SELECT * FROM episodes", conn)
    parquet = parquet.sort_values("episode_tconst").reset_index(drop=True)
    sql = sql.sort_values("episode_tconst").reset_index(drop=True)
    return parquet, sql


def test_same_columns_in_the_same_order(both_tables):
    parquet, sql = both_tables
    assert list(sql.columns) == list(parquet.columns)


def test_same_episodes(both_tables):
    parquet, sql = both_tables
    assert len(sql) == len(parquet)
    assert sql["episode_tconst"].equals(parquet["episode_tconst"])


@pytest.mark.parametrize("column", [
    "show_tconst", "show_title", "genres", "start_year", "end_year", "ongoing",
    "season_number", "episode_number", "overall_order",
    "average_rating", "num_votes",
])
def test_same_value_in_every_row(both_tables, column):
    """SQLite hands back its own types (ongoing as 0/1, a nullable year as a
    float), so values are compared, not dtypes. Both-null counts as equal."""
    parquet, sql = both_tables
    expected = parquet[column]
    actual = sql[column].astype(bool) if column == "ongoing" else sql[column]
    equal = (expected == actual).fillna(False) | (expected.isna() & actual.isna())
    assert equal.all(), f"{column}: {int((~equal).sum())} rows differ"
