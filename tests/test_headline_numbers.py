"""The published numbers, recomputed from the parquet.

The README claims a figure "cannot quietly drift away from the numbers in the
text" because every figure recomputes its own inputs. That is true, and it was
still only a convention -- nothing enforced it. This file does: every number in
the README's findings table is recomputed here from data/processed/ and checked
against what the documents say.

If a filter, a weighting scheme or a threshold changes, these fail, and the
prose has to be updated deliberately rather than silently going stale.

Run from the repository root:  pytest
"""

import numpy as np
import pandas as pd
import pytest

CLEAR = 0.5        # the clear-decline / clear-rise threshold
MIN_SEASON_EP = 4  # a season needs a body to compare its finale against


@pytest.fixture(scope="module")
def episodes():
    return pd.read_parquet("data/processed/episodes.parquet")


@pytest.fixture(scope="module")
def slopes(episodes):
    """Recompute every show's sqrt(votes)-weighted trend slope from scratch."""
    records = []
    for show_id, g in episodes.groupby("show_tconst"):
        g = g.sort_values("overall_order")
        n = len(g)
        y = g["average_rating"].to_numpy(dtype=float)
        w = np.sqrt(g["num_votes"].to_numpy(dtype=float))
        x = (g["overall_order"].to_numpy(dtype=float) - 1) / (n - 1)
        total = w.sum()
        x_bar = (w * x).sum() / total
        y_bar = (w * y).sum() / total
        slope = (w * (x - x_bar) * (y - y_bar)).sum() / (w * (x - x_bar) ** 2).sum()
        records.append({"show_id": show_id, "slope": slope})
    return pd.DataFrame(records)


def test_stored_slopes_match_a_fresh_recompute(slopes):
    """The guarantee the README makes. Every downstream analysis and all nine
    figures read this file; if it ever stops matching the parquet, everything
    built on it is quietly wrong."""
    stored = pd.read_json("data/processed/_phase2_slopes_full.json")
    merged = stored.merge(slopes, on="show_id", suffixes=("_stored", "_fresh"))
    assert len(merged) == len(stored)
    assert np.allclose(merged["slope_stored"], merged["slope_fresh"], atol=1e-9)


def test_the_headline_three_way_split(slopes):
    """README: 16.9% clearly decline, 57.4% essentially flat, 25.7% clearly rise."""
    s = slopes["slope"]
    assert round(100 * (s <= -CLEAR).mean(), 1) == 16.9
    assert round(100 * ((s > -CLEAR) & (s < CLEAR)).mean(), 1) == 57.4
    assert round(100 * (s >= CLEAR).mean(), 1) == 25.7


def test_the_median_show_drifts_slightly_up(slopes):
    """The essay's "the median show doesn't sag at all. It drifts slightly up"."""
    assert round(float(slopes["slope"].median()), 3) == 0.109


def test_halves_of_a_show_track_each_other(episodes):
    """Essay §2: a +0.79 correlation between disjoint halves, and the
    top-quartile starter giving up 0.07 of a point. The disjointness is the
    whole point of the test -- it is what the discarded -0.37 result lacked."""
    rows = []
    for _, g in episodes.groupby("show_tconst"):
        g = g.sort_values("overall_order")
        half = len(g) // 2
        rows.append({
            "first": g.iloc[:half]["average_rating"].mean(),
            "second": g.iloc[half:]["average_rating"].mean(),
        })
    halves = pd.DataFrame(rows)
    assert round(halves["first"].corr(halves["second"]), 2) == 0.79

    top = halves[halves["first"] >= halves["first"].quantile(0.75)]
    assert round(top["second"].mean() - top["first"].mean(), 2) == -0.07


def test_season_finales_beat_their_own_season(episodes):
    """README: season finales win 72.6% of the time."""
    premiums = []
    for _, g in episodes.groupby("show_tconst"):
        for _, season in g.groupby("season_number"):
            season = season.sort_values("episode_number")
            if len(season) < MIN_SEASON_EP:
                continue
            ratings = season["average_rating"].to_numpy(dtype=float)
            premiums.append(ratings[-1] - ratings[:-1].mean())
    assert round(100 * np.mean(np.array(premiums) > 0), 1) == 72.6


def test_series_finales_usually_rise(episodes):
    """README: series finales rise 71.6% of the time."""
    effects = []
    for _, g in episodes.groupby("show_tconst"):
        final = g[g["season_number"] == g["season_number"].max()]
        final = final.sort_values("episode_number")
        if len(final) < MIN_SEASON_EP:
            continue
        ratings = final["average_rating"].to_numpy(dtype=float)
        effects.append(ratings[-1] - ratings[:-1].mean())
    assert round(100 * np.mean(np.array(effects) > 0), 1) == 71.6


def test_the_final_season_is_close_to_a_coin_flip(episodes):
    """README: 50.6% down, 49.2% up, and only 12.6% lose half a point or more.
    Ended shows only -- an unfinished show has no final season yet."""
    ended = episodes[~episodes["ongoing"]]
    deltas = []
    for _, g in ended.groupby("show_tconst"):
        final_season = g["season_number"].max()
        final = g[g["season_number"] == final_season]["average_rating"]
        rest = g[g["season_number"] != final_season]["average_rating"]
        if len(rest) == 0:
            continue
        deltas.append(final.mean() - rest.mean())
    deltas = np.array(deltas)
    assert round(100 * (deltas < 0).mean(), 1) == 50.6
    assert round(100 * (deltas > 0).mean(), 1) == 49.2
    assert round(100 * (deltas <= -0.5).mean(), 1) == 12.6
    # The two shares do not sum to 100: six series end exactly level. Counting
    # them as risers is what put 49.4% into the documents.
    assert (deltas == 0).sum() == 6


def test_length_and_era_effects_keep_their_published_size(slopes, episodes):
    """README: every extra season costs 0.026 of a point, every decade newer
    adds 0.048. Reported from the genre model, so the genre dummies are
    included here too -- dropping them would change the estimates."""
    per_show = episodes.groupby("show_tconst").agg(
        n_season=("season_number", "nunique"),
        start_year=("start_year", "first"),
        ongoing=("ongoing", "first"),
        genres=("genres", "first"),
    ).reset_index()
    d = slopes.merge(per_show, left_on="show_id", right_on="show_tconst")
    d = d.dropna(subset=["start_year", "genres"])

    genres = ["Documentary", "Biography", "Horror", "Family", "Mystery", "Romance",
              "Fantasy", "History", "Sci-Fi", "Crime", "Drama", "Comedy",
              "Thriller", "Adventure", "Action", "Animation"]
    columns = [
        d["start_year"].astype(float) - d["start_year"].astype(float).mean(),
        d["n_season"].astype(float),
        d["ongoing"].astype(float),
    ] + [d["genres"].str.split(",").apply(lambda gs: float(g in gs)) for g in genres]

    X = np.column_stack([np.ones(len(d))] + [c.to_numpy() for c in columns])
    beta = np.linalg.inv(X.T @ X) @ X.T @ d["slope"].to_numpy(dtype=float)

    assert round(float(beta[1]), 4) == 0.0048   # per year -> 0.048 per decade
    assert round(float(beta[2]), 3) == -0.026   # per extra season
