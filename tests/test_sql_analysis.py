"""The published findings, recomputed in SQL.

Every query in sql/analysis/ runs against the committed episode table, loaded
into an in-memory SQLite database, and must reproduce what the documents say.
Unlike tests/test_sql_build.py this needs no raw data, so it runs in CI.

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


def test_finales_beat_their_season_counted_in_integers(conn):
    """72.5% of season finales win, 71.3% of series finales rise.

    This query is what found that the figures were once published as 72.6% and
    71.6%: 91 season finales sit exactly on their season's mean, and the float
    comparison in the Python had counted 23 of them (7 series finales) as wins.
    Compared as integers, a tie is a tie. The correction is recorded in
    docs/decisions.md; the Python now uses a tolerance and agrees."""
    row = one_row(conn, "finales.sql")
    assert row["seasons"] == 12_931
    assert row["series_finales"] == 3_082
    assert row["season_finale_ties"] == 91
    assert row["series_finale_ties"] == 23
    assert row["season_finale_wins"] == 9_370
    assert row["series_finale_rises"] == 2_199
    assert row["pct_season_finale_wins"] == 72.5
    assert row["pct_series_finale_rises"] == 71.3


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


def test_show_pages_sum_back_to_the_published_findings(conn):
    """sql/analysis/show_pages.sql is what the show-lookup app prints, one show
    at a time. Each column mirrors an analysis query, so adding the table back
    up must land on the published numbers -- otherwise a page could tell a
    reader something about their show that the essay's totals contradict."""
    pages = pd.read_sql("SELECT * FROM show_pages", conn)
    assert len(pages) == 3_234
    assert pages["show_tconst"].is_unique

    assert (pages["verdict"] == "decline").sum() == 545
    assert round(100 * (pages["verdict"] == "flat").mean(), 1) == 57.4
    assert round(100 * (pages["verdict"] == "rise").mean(), 1) == 25.7

    ended = pages[pages["ongoing"] == 0]
    assert len(ended) == 2_710
    assert pages.loc[pages["ongoing"] == 1, "final_season_sign"].isna().all()
    assert round(100 * (ended["final_season_sign"] < 0).mean(), 1) == 50.5
    assert round(100 * (ended["final_season_sign"] > 0).mean(), 1) == 49.2
    assert (ended["final_season_sign"] == 0).sum() == 10

    assert pages["finales_counted"].sum() == 12_931
    assert pages["finales_won"].sum() == 9_370
    assert pages["series_finale_rose"].notna().sum() == 3_082
    assert pages["series_finale_rose"].sum() == 2_199

    by_tier = pages.groupby("audience_tier")["verdict"].apply(lambda v: round(100 * (v == "decline").mean(), 1))
    assert by_tier.tolist() == [14.8, 15.1, 24.7, 43.3]


def test_show_pages_trend_line_matches_the_python_fit(conn):
    """The app draws each show's line from slope and intercept; both must be the
    numpy fit's. The intercept is new here, so it is checked from scratch."""
    pages = pd.read_sql("SELECT show_tconst, slope, intercept FROM show_pages", conn).set_index("show_tconst")
    episodes = pd.read_parquet("data/processed/episodes.parquet")
    for show_id, g in episodes.groupby("show_tconst"):
        n = len(g)
        x = (g["overall_order"].to_numpy(dtype=float) - 1) / (n - 1)
        y = g["average_rating"].to_numpy(dtype=float)
        w = np.sqrt(g["num_votes"].to_numpy(dtype=float))
        x_bar, y_bar = (w * x).sum() / w.sum(), (w * y).sum() / w.sum()
        b = (w * (x - x_bar) * (y - y_bar)).sum() / (w * (x - x_bar) ** 2).sum()
        assert abs(pages.at[show_id, "slope"] - b) < 1e-9
        assert abs(pages.at[show_id, "intercept"] - (y_bar - b * x_bar)) < 1e-9


def test_show_pages_placement_among_all_shows(conn):
    """"Steeper decline than 97% of shows" must mean exactly that: the share of
    the other shows whose slope is higher."""
    pages = pd.read_sql("SELECT slope, share_declining_less, share_rising_less FROM show_pages", conn)
    slopes = pages["slope"].to_numpy()
    n = len(slopes)
    for s, down, up in pages.sample(200, random_state=0).itertuples(index=False):
        assert abs(down - (slopes > s).sum() / n) < 1e-12
        assert abs(up - (slopes < s).sum() / n) < 1e-12
