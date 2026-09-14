"""The published findings, recomputed in SQL.

Every query in sql/analysis/ runs against the committed episode table, loaded
into an in-memory SQLite database, and must reproduce what the documents say.
Unlike tests/test_sql_build.py this needs no raw data, so it runs in CI.

One finding does not reproduce to the published decimal, on purpose -- see
test_finales_exact_count_differs_from_the_published_float_count.

Run from the repository root:  pytest
"""

import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "sql")
from run_analysis import open_analysis_db, query  # noqa: E402


@pytest.fixture(scope="module")
def conn():
    connection = open_analysis_db()
    yield connection
    connection.close()


def one_row(conn, name):
    return query(conn, name).iloc[0]


def test_every_show_slope_matches_the_python_fit(conn):
    """The closed-form SQL slope against the stored numpy fit, show by show."""
    sql = pd.read_sql("SELECT show_tconst AS show_id, slope FROM show_slopes", conn)
    stored = pd.read_json("data/processed/_phase2_slopes_full.json")
    merged = stored.merge(sql, on="show_id", suffixes=("_python", "_sql"))
    assert len(sql) == len(stored) == len(merged) == 3_234
    assert np.allclose(merged["slope_python"], merged["slope_sql"], rtol=0, atol=1e-9)


def test_headline_three_way_split_and_median(conn):
    row = one_row(conn, "slope_split.sql")
    assert row["shows"] == 3_234
    assert row["pct_clear_decline"] == 16.9
    assert row["pct_flat"] == 57.4
    assert row["pct_clear_rise"] == 25.7
    assert row["n_clear_decline"] == 545
    assert row["median_slope"] == 0.109


def test_finales_exact_count_differs_from_the_published_float_count(conn):
    """The published 72.6% and 71.6% count some exact ties as wins.

    A finale "beats its season" when its rating is above the mean of the other
    episodes. 91 season finales sit exactly on that mean. The Python computes
    `finale - mean(rest) > 0` in floating point, where an exact tie comes out
    as about +1e-15 or -1e-15 at random; 23 of the 91 land above zero and are
    counted as wins, 7 of them series finales. The SQL compares integers
    (ratings in tenths, cross-multiplied), so a tie is a tie and not a win.

    Exact:      72.5% of season finales win, 71.3% of series finales rise.
    Published:  72.6% and 71.6% -- the exact counts plus those 23 and 7 ties.

    This pins both the exact figures and the explanation of the gap, so the
    difference stays documented until the published numbers are corrected.
    """
    row = one_row(conn, "finales.sql")
    seasons, series = row["seasons"], row["series_finales"]
    assert seasons == 12_931
    assert series == 3_082
    assert row["season_finale_ties"] == 91
    assert row["series_finale_ties"] == 23

    assert row["pct_season_finale_wins"] == 72.5
    assert row["pct_series_finale_rises"] == 71.3

    # Adding back exactly the ties that floating point called wins recovers
    # the published figures.
    assert round(100 * (row["season_finale_wins"] + 23) / seasons, 1) == 72.6
    assert round(100 * (row["series_finale_rises"] + 7) / series, 1) == 71.6


def test_final_season_is_a_coin_flip_with_ten_exact_ties(conn):
    """Integer arithmetic finds the ten ties directly, without the tolerance
    tests/test_headline_numbers.py needs."""
    row = one_row(conn, "final_season.sql")
    assert row["ended_shows"] == 2_710
    assert row["pct_final_season_lower"] == 50.5
    assert row["pct_final_season_higher"] == 49.2
    assert row["exactly_level"] == 10
    assert row["pct_loses_half_a_point"] == 12.6


def test_last_season_is_best_more_often_than_the_first(conn):
    row = one_row(conn, "best_season.sql")
    assert row["shows"] == 3_234
    assert row["pct_first_season_best"] == 27.1
    assert row["pct_last_season_best"] == 37.2


def test_clear_decline_climbs_with_audience_size(conn):
    tiers = query(conn, "popularity.sql")
    assert tiers["shows"].tolist() == [1_184, 1_545, 445, 60]
    assert tiers["pct_clear_decline"].tolist() == [14.8, 15.1, 24.7, 43.3]
