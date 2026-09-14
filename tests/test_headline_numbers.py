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

import math

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


def test_the_headline_gloss_is_about_one_in_six_not_fewer(slopes):
    """The verbal shorthand for 16.9%, checked against the fraction it claims.

    Every document glossed the headline as "fewer than one in six". It is not:
    one sixth of 3,234 shows is 539 and the clear decliners number 545, so the
    share sits just *above* one in six, not below. A gloss is not decoration --
    it is the version of the finding that travels, and this one travelled onto
    the README's first screen and into the repository description.

    The number was always right; only the sentence around it was wrong, which
    is exactly the failure the essay's §7 warns about. The wording is pinned
    here so it cannot drift back if the threshold or the filters ever move the
    share to the other side of 1/6 -- at which point this test fails and the
    prose gets revisited deliberately.

    WHAT THIS DOES NOT COVER -- read before trusting it.

    The phrase lived on six surfaces. Five are files and are checked below. The
    sixth is the **GitHub repository description**, which is not a file in this
    repository, is edited through GitHub rather than through a commit, and
    feeds the repository card's og:description. `pytest` cannot see it, and no
    amount of care here will change that.

    A CI step calling the API was considered and rejected. The fault it would
    guard against -- someone edits the description and does not update the
    prose -- involves no commit, so CI would not run at the moment it happens;
    it would instead fail unrelated pushes for a value nobody touched, and it
    would end the suite's one real guarantee, that it runs on a fresh clone
    with no network and no raw data.

    So that surface is handled by procedure, not by code. The procedure, with
    the canonical text to copy from, is in docs/decisions.md under "Changing
    the headline claim". Treating an unautomatable surface as automated is
    worse than leaving it visibly manual.
    """
    from pathlib import Path

    s = slopes["slope"]
    n_decline = int((s <= -CLEAR).sum())
    one_sixth = len(s) / 6
    assert n_decline > one_sixth, (
        f"{n_decline} clear decliners against a one-in-six mark of "
        f"{one_sixth:.1f}: 'fewer than one in six' would now be true and the "
        "prose says 'about'"
    )

    # decisions.md is deliberately absent: it is the record of what went wrong
    # and has to be able to quote the wrong wording, exactly as it quotes the
    # superseded 49.4% elsewhere. Everything here is a document that states the
    # finding rather than its history.
    #
    # _config.yml is here because leaving it out let the phrase straight back
    # in. The site-wide `description:` was written from memory in the same
    # session that corrected everything else, and this check passed while the
    # wrong gloss sat in the repository -- latent rather than live, because
    # every page carries its own front-matter description, but one page without
    # one would have published it. A list of "the documents" is the wrong unit:
    # the unit is every file that states the finding to a reader, and site
    # metadata does.
    published = ["README.md", "index.md", "_config.yml", "docs/essay.md",
                 "docs/technical_report.md", "docs/technical_report.tex"]
    offenders = []
    for name in published:
        # The claim wraps across lines in several of these files.
        text = " ".join(Path(name).read_text(encoding="utf-8").split())
        if "fewer than one in six" in text.lower():
            offenders.append(name)
    assert not offenders, (
        "the share is above one in six, so this gloss is false: " f"{offenders}"
    )


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


def season_contrasts(episodes):
    """Per season of >= 4 episodes: the finale's and the premiere's premium over
    the rest of that season, and whether it is the show's final season."""
    rows = []
    for _, g in episodes.groupby("show_tconst"):
        last_season = g["season_number"].max()
        for number, season in g.groupby("season_number"):
            season = season.sort_values("episode_number")
            if len(season) < MIN_SEASON_EP:
                continue
            ratings = season["average_rating"].to_numpy(dtype=float)
            rows.append({
                "finale": ratings[-1] - ratings[:-1].mean(),
                "premiere": ratings[0] - ratings[1:].mean(),
                "is_final_season": number == last_season,
            })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def contrasts(episodes):
    return season_contrasts(episodes)


# A premium is a rating minus a mean of one-decimal ratings. When the two are
# equal as rationals, float arithmetic leaves +/-1e-15 rather than 0, so every
# comparison below goes through a tolerance -- the same one the final-season
# test needs. The smallest real non-zero premium is 0.1 / (episodes - 1).
TIE_TOL = 1e-9


def test_season_finales_beat_their_own_season(contrasts):
    """README: season finales win 72.5% of the time.

    Published as 72.6% until the SQL reproduction (sql/analysis/finales.sql)
    compared the ratings as integers: 91 finales equal their season's mean
    exactly, and `> 0` had counted the 23 that float arithmetic put at +1e-15 as
    wins. The last assertion keeps that failure visible."""
    finale = contrasts["finale"]
    assert len(finale) == 12_931
    assert int((finale.abs() <= TIE_TOL).sum()) == 91
    assert round(100 * (finale > TIE_TOL).mean(), 1) == 72.5
    assert round(100 * (finale > 0).mean(), 1) == 72.6   # the old, tie-blind count


def test_series_finales_usually_rise(contrasts):
    """README: series finales rise 71.3% of the time (published as 71.6%, for
    the same reason: 7 of their 23 exact ties were counted as rises)."""
    series = contrasts.loc[contrasts["is_final_season"], "finale"]
    assert len(series) == 3_082
    assert int((series.abs() <= TIE_TOL).sum()) == 23
    assert round(100 * (series > TIE_TOL).mean(), 1) == 71.3
    assert round(100 * (series > 0).mean(), 1) == 71.6   # the old, tie-blind count


def test_premieres_and_finale_flops_keep_their_published_size(contrasts):
    """Technical report §4.3: premieres beat their season 43.1% of the time, and
    9.5% of series finales fall half a point or more. Neither was pinned before,
    so neither failed when the tie-blind comparison put them at 43.3% and 9.4%."""
    assert round(100 * (contrasts["premiere"] > TIE_TOL).mean(), 1) == 43.1
    series = contrasts.loc[contrasts["is_final_season"], "finale"]
    assert round(100 * (series <= -0.5 + TIE_TOL).mean(), 1) == 9.5


def test_the_superseded_finale_shares_are_gone_from_the_documents():
    """72.6% and 71.6% were stated on every surface that reports the finding.

    Covers the files a reader sees: README, the essay, the technical report in
    both sources, the outline and the site pages. Does NOT cover
    docs/technical_report.pdf (binary; it is compiled from the .tex, which is
    checked here and in test_report_source.py) or the rendered figures (fig03
    recomputes its labels from the parquet with the same tolerance).
    docs/decisions.md is excluded on purpose: it records the correction and has
    to be able to quote the old figures."""
    from pathlib import Path

    published = ["README.md", "index.md", "_config.yml", "docs/essay.md",
                 "docs/technical_report.md", "docs/technical_report.tex",
                 "docs/report_outline.md"]
    offenders = [
        f"{name}: {old}"
        for name in published
        for old in ("72.6", "71.6")
        if old in Path(name).read_text(encoding="utf-8")
    ]
    assert not offenders, f"superseded finale shares still stated: {offenders}"


def test_the_final_season_is_close_to_a_coin_flip(episodes):
    """README: 50.5% down, 49.2% up, and only 12.6% lose half a point or more.
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

    # Ties are compared against a tolerance, not against exact zero. A tie means
    # two means of one-decimal ratings are equal as rationals, and float
    # arithmetic renders four of them as +/-1e-15. Testing `== 0` reports 6 ties;
    # the true count is 10, and pandas' to_json rounding reported 8 to whatever
    # read the exported file. Three answers, all artifacts of comparing to zero.
    TOL = 1e-9
    assert (np.abs(deltas) <= TOL).sum() == 10
    assert (deltas == 0).sum() == 6          # the float-equality count, for contrast

    assert round(100 * (deltas < -TOL).mean(), 1) == 50.5
    assert round(100 * (deltas > TOL).mean(), 1) == 49.2
    assert round(100 * (deltas <= -0.5).mean(), 1) == 12.6
    # The three shares must account for every series exactly once.
    assert ((deltas < -TOL).sum() + (deltas > TOL).sum()
            + (np.abs(deltas) <= TOL).sum()) == len(deltas)


def test_the_belief_fits_the_famous_shows(episodes, slopes):
    """README: clear decline climbs from 15% among obscure shows to 43% among
    the 60 household names. This is the row that reconciles the headline with
    the reader's own experience, so it is worth pinning."""
    votes = episodes.groupby("show_tconst")["num_votes"].sum().rename("total_votes")
    d = slopes.merge(votes, left_on="show_id", right_index=True)
    share = lambda sub: round(100 * (sub["slope"] <= -CLEAR).mean(), 1)

    assert share(d[d["total_votes"] < 5_000]) == 14.8
    assert share(d[(d["total_votes"] >= 5_000) & (d["total_votes"] < 50_000)]) == 15.1
    assert share(d[(d["total_votes"] >= 50_000) & (d["total_votes"] < 500_000)]) == 24.7

    top = d[d["total_votes"] >= 500_000]
    assert len(top) == 60
    assert share(top) == 43.3
    # The gradient is the claim, so it must be monotone, not merely high at the top.
    tiers = [d[d["total_votes"] < 5_000],
             d[(d["total_votes"] >= 5_000) & (d["total_votes"] < 50_000)],
             d[(d["total_votes"] >= 50_000) & (d["total_votes"] < 500_000)],
             top]
    shares = [share(t) for t in tiers]
    assert shares == sorted(shares)


def test_only_two_genres_survive_the_multiplicity_correction(slopes, episodes):
    """The genre model screens 16 coefficients at once, so the documents report
    Animation and Adventure as the only Bonferroni survivors, and explicitly
    withdraw Biography. If a future change re-widens that set, the prose in the
    essay, the report and Appendix A all become wrong at once."""
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
    ] + [d["genres"].str.split(",").apply(lambda gs, g=g: float(g in gs)) for g in genres]

    X = np.column_stack([np.ones(len(d))] + [c.to_numpy() for c in columns])
    y = d["slope"].to_numpy(dtype=float)
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    sigma2 = resid @ resid / (len(d) - X.shape[1])
    se = np.sqrt(np.diag(sigma2 * XtX_inv))

    # Genre coefficients start after intercept + year + seasons + ongoing.
    alpha_corrected = 0.05 / len(genres)
    survivors = set()
    for i, g in enumerate(genres, start=4):
        p = math.erfc(abs(beta[i] / se[i]) / math.sqrt(2))
        if p < alpha_corrected:
            survivors.add(g)

    assert survivors == {"Animation", "Adventure"}
    # Named separately because a document explicitly retracts it.
    assert "Biography" not in survivors


def test_noise_inflates_the_apparent_decline_share(episodes):
    """Technical report §5.6. The claim is directional: estimation noise pushes
    mass out of the flat middle band, so the observed 16.9% overstates the true
    clear-decline share. Tested the assumption-free way -- feed the estimates
    back as if they were the truth, add their own noise, and the expected
    observed share must come out ABOVE what we actually observe.

    Guards against the mistake the first version of §5.6 made: reporting a
    shrinkage-based split, which understates both tails mechanically."""
    rows = []
    for _, g in episodes.groupby("show_tconst"):
        g = g.sort_values("overall_order")
        n = len(g)
        y = g["average_rating"].to_numpy(dtype=float)
        w = np.sqrt(g["num_votes"].to_numpy(dtype=float))
        x = (g["overall_order"].to_numpy(dtype=float) - 1) / (n - 1)
        total = w.sum()
        x_bar = (w * x).sum() / total
        y_bar = (w * y).sum() / total
        s_xx = (w * (x - x_bar) ** 2).sum()
        b = (w * (x - x_bar) * (y - y_bar)).sum() / s_xx
        a = y_bar - b * x_bar
        r = y - (a + b * x)
        rows.append((b, math.sqrt(((w * r ** 2).sum() / (n - 2)) / s_xx)))
    slope = np.array([r[0] for r in rows])
    se = np.array([r[1] for r in rows])

    observed = (slope <= -CLEAR).mean()
    # Expected share of noisy estimates below the cut if the truth were `slope`.
    phi = np.array([0.5 * (1 + math.erf(q / math.sqrt(2)))
                    for q in (-CLEAR - slope) / se])
    assert phi.mean() > observed          # the direction the report claims
    assert round(100 * phi.mean(), 1) == 18.1
    assert round(100 * observed, 1) == 16.9

    # And the variance decomposition the section leads with: ~10% noise.
    var_err = (se ** 2).mean()
    assert round(100 * var_err / slope.var(ddof=1)) == 10


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
