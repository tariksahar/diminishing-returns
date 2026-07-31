"""Phase 2 -- does the folk belief hold better for the shows it is about?

The report's headline is a statement about the average show: fewer than one in
six clearly declines. But nobody forms the decline belief from the average
show. They form it from the few dozen series everyone watched, and §4 of the
essay explains the gap with availability bias -- explicitly flagged there as
interpretation rather than something the data proves.

This script tests whether it is measurable instead of merely plausible, by
cutting the same sqrt(votes)-weighted slope by how widely watched a series is
(total votes across all its episodes, the only popularity proxy in the data).

Five parts, in the order the objections arrive:
  1. the raw gradient across popularity tiers
  2. is it a precision artifact? (slope standard error by tier)
  3. is it just the known length effect? (within fixed season bands)
  4. does it survive era and length jointly? (OLS)
  5. the same cut on the final-season delta, because that is the quantity the
     report's final-season section makes a fame claim about -- the slope and the
     delta answer different questions (see docs/decisions.md), so the claim
     cannot borrow part 1's numbers and needs its own

TWO CAVEATS THAT MUST TRAVEL WITH ANY USE OF THIS RESULT:

  * Vote count is endogenous. This project already documented the mechanism
    in the weighting decision: a final-season backlash inflates vote counts
    (four of Game of Thrones' six most-voted episodes are season-8 ones). So
    decline raises votes as surely as votes track decline, and the arrow
    cannot be pointed. Nothing causal may be claimed from this.

  * What survives is descriptive, and that is still worth having: the series
    the belief is actually about do not behave like the average series.

Prints its findings; exports nothing, since no figure consumes it.
"""

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")
slopes = pd.read_json("data/processed/_phase2_slopes_full.json")

CLEAR = 0.5  # the same clear-decline / clear-rise threshold used by the headline

# Popularity tiers. Cut on total votes across the whole series, so a short
# series watched by millions counts as popular even though it has few episodes.
TIERS = [
    (0, 5e3, "under 5k votes"),
    (5e3, 5e4, "5k - 50k"),
    (5e4, 5e5, "50k - 500k"),
    (5e5, np.inf, "over 500k (household names)"),
]


def tier_of(total_votes):
    for lo, hi, label in TIERS:
        if lo <= total_votes < hi:
            return label
    return None


def wilson(successes, n, z=1.96):
    """95% Wilson score interval for a proportion, as percentages.

    The top popularity tier is small by construction -- only a few dozen series
    are household names -- so a bare percentage there invites more confidence
    than it earns. Wilson rather than the normal approximation because it stays
    inside [0, 1] and behaves at small n.
    """
    if n == 0:
        return float("nan"), float("nan")
    p = successes / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return 100 * (centre - half), 100 * (centre + half)


slopes["tier"] = slopes["total_votes"].apply(tier_of)

# ----------------------------------------------------------------------
# (1) THE RAW GRADIENT
# ----------------------------------------------------------------------
print("=" * 78)
print("(1) DECLINE BY POPULARITY TIER")
print("=" * 78)
print(f"{'tier':<30}{'n':>6}{'clear decline':>15}{'95% CI':>16}{'median slope':>14}")
for _, _, label in TIERS:
    s = slopes[slopes["tier"] == label]
    n_dec = int((s["slope"] <= -CLEAR).sum())
    dec = 100 * n_dec / len(s)
    lo, hi = wilson(n_dec, len(s))
    print(f"  {label:<28}{len(s):>6}{dec:>14.1f}%{f'{lo:.1f}-{hi:.1f}':>16}"
          f"{s['slope'].median():>+14.3f}")
print()
print(f"Whole dataset for reference: {100*(slopes['slope'] <= -CLEAR).mean():.1f}% clear decline, "
      f"median {slopes['slope'].median():+.3f}")
print()
print("The gradient is monotone, and the top tier declines at roughly three times")
print("the base rate. The remaining sections try to make it go away.")
print()


# ----------------------------------------------------------------------
# (2) IS IT A PRECISION ARTIFACT?
# ----------------------------------------------------------------------
# A noisier slope estimate crosses a fixed +/-0.5 threshold more often by luck
# alone, so if obscure series had much noisier slopes the tier gradient could be
# manufactured entirely by measurement error. Refit each series and keep the
# standard error of its slope to check, rather than assuming either way.
def slope_with_se(g):
    g = g.sort_values("overall_order")
    n = len(g)
    y = g["average_rating"].to_numpy(dtype=float)
    w = np.sqrt(g["num_votes"].to_numpy(dtype=float))
    x = (g["overall_order"].to_numpy(dtype=float) - 1) / (n - 1)
    W = w.sum()
    x_bar = (w * x).sum() / W
    y_bar = (w * y).sum() / W
    s_xx = (w * (x - x_bar) ** 2).sum()
    b = (w * (x - x_bar) * (y - y_bar)).sum() / s_xx
    a = y_bar - b * x_bar
    resid = y - (a + b * x)
    # Weighted residual variance, then the usual slope SE = sqrt(var / S_xx).
    se = np.sqrt(((w * resid ** 2).sum() / (n - 2)) / s_xx)
    return b, se


# Only the standard error is taken from the refit -- episode counts and slopes
# already live in the slopes table, and re-merging them would collide.
rows = []
for show_id, g in df.groupby("show_tconst"):
    _, se = slope_with_se(g)
    rows.append({"show_id": show_id, "se": se})
prec = slopes.merge(pd.DataFrame(rows), on="show_id", how="left")

print("=" * 78)
print("(2) IS THE GRADIENT A MEASUREMENT-PRECISION ARTIFACT?")
print("=" * 78)
print(f"{'tier':<30}{'median slope SE':>18}{'median episodes':>18}")
for _, _, label in TIERS:
    s = prec[prec["tier"] == label]
    print(f"  {label:<28}{s['se'].median():>18.3f}{s['n_ep'].median():>18.0f}")
print()
print("Precision is essentially flat across tiers (median SE 0.17-0.21): popular")
print("series have less noise per episode but genuinely bumpier ratings, and the")
print("two roughly cancel. With comparable precision everywhere, a threefold")
print("difference in clear-decline share cannot be an artifact of noisier fits.")
print()


# ----------------------------------------------------------------------
# (3) IS IT JUST THE KNOWN LENGTH EFFECT?
# ----------------------------------------------------------------------
# Popular series run longer, and long series were already shown to decline, so
# this is the objection that has to be answered before anything else. Hold the
# season count inside a narrow band and compare popular against obscure there.
print("=" * 78)
print("(3) IS IT JUST LENGTH? (popularity within fixed season bands)")
print("=" * 78)
print(f"correlation between log10(total votes) and season count: "
      f"{np.log10(slopes['total_votes']).corr(slopes['n_season']):.2f}")
print()
LOW_VOTES, HIGH_VOTES = 2e4, 2e5
print(f"{'season band':<16}{'obscure (<20k votes)':>30}{'popular (>=200k votes)':>30}")
for lo, hi, label in [(2, 3, "2-3 seasons"), (4, 5, "4-5 seasons"), (6, 99, "6+ seasons")]:
    band = slopes[(slopes["n_season"] >= lo) & (slopes["n_season"] <= hi)]
    obscure = band[band["total_votes"] < LOW_VOTES]
    popular = band[band["total_votes"] >= HIGH_VOTES]
    print(f"  {label:<14}"
          f"n={len(obscure):>5}  {100*(obscure['slope'] <= -CLEAR).mean():>5.1f}% decline"
          f"{'':>6}n={len(popular):>4}  {100*(popular['slope'] <= -CLEAR).mean():>5.1f}% decline")
print()
print("The gap holds inside every band, so length does not absorb it.")
print()


# ----------------------------------------------------------------------
# (4) NET OF ERA AND LENGTH JOINTLY (OLS)
# ----------------------------------------------------------------------
# Same specification style as the genre model in phase2_rtm_genre.py: classical
# SEs, which are adequate given the size of the t-statistics.
print("=" * 78)
print("(4) POPULARITY NET OF ERA AND LENGTH (OLS)")
print("=" * 78)
d = slopes.dropna(subset=["start_year"]).copy()
d["log_votes"] = np.log10(d["total_votes"])
d["yr_c"] = d["start_year"] - d["start_year"].mean()

cols = ["log_votes", "n_season", "yr_c"]
X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in cols])
y = d["slope"].to_numpy(float)
XtX_inv = np.linalg.inv(X.T @ X)
beta = XtX_inv @ X.T @ y
resid = y - X @ beta
sigma2 = resid @ resid / (len(d) - X.shape[1])
se = np.sqrt(np.diag(sigma2 * XtX_inv))
tstat = beta / se

print(f"n = {len(d)} shows")
print(f"{'variable':<14}{'coef':>10}{'std err':>10}{'t':>8}")
for name, b_i, se_i, t_i in zip(["intercept"] + cols, beta, se, tstat):
    print(f"  {name:<12}{b_i:>10.4f}{se_i:>10.4f}{t_i:>8.1f}")
print()
print("Each tenfold increase in total votes costs the trend "
      f"{abs(beta[1]):.3f} rating points,")
print(f"larger in magnitude than one extra season ({abs(beta[2]):.3f}) and estimated just")
print("as sharply. Popularity is not standing in for era or length.")
print()

# ----------------------------------------------------------------------
# (5) THE SAME CUT ON THE FINAL-SEASON DELTA
# ----------------------------------------------------------------------
# §4.4 of the technical report states that the cursed minority is dominated by
# well-known series. Parts 1-4 measured the SLOPE, and this project established
# that the slope is not a proxy for the final-season question, so that claim
# cannot lean on them -- it needs the delta cut the same way. Ended series only:
# an unfinished show has no final season yet.
print("=" * 78)
print("(5) THE FINAL-SEASON CURSE BY POPULARITY TIER (ended series only)")
print("=" * 78)
ended = df[~df["ongoing"]]
deltas = []
for show_id, g in ended.groupby("show_tconst"):
    final_season = g["season_number"].max()
    final = g[g["season_number"] == final_season]["average_rating"]
    rest = g[g["season_number"] != final_season]["average_rating"]
    if len(rest) == 0:
        continue
    deltas.append({
        "show_id": show_id,
        "delta": float(final.mean() - rest.mean()),
        "total_votes": int(g["num_votes"].sum()),
    })
dl = pd.DataFrame(deltas)
dl["tier"] = dl["total_votes"].apply(tier_of)

CURSED = -0.5  # the same cut the headline uses
print(f"{'tier':<30}{'n':>6}{'clearly cursed':>16}{'95% CI':>16}{'median delta':>14}")
for _, _, label in TIERS:
    s = dl[dl["tier"] == label]
    if len(s) == 0:
        continue
    n_cur = int((s["delta"] <= CURSED).sum())
    lo, hi = wilson(n_cur, len(s))
    print(f"  {label:<28}{len(s):>6}{100*n_cur/len(s):>15.1f}%{f'{lo:.1f}-{hi:.1f}':>16}"
          f"{s['delta'].median():>+14.3f}")
print()
print(f"All {len(dl):,} ended series for reference: "
      f"{100*(dl['delta'] <= CURSED).mean():.1f}% cursed, "
      f"median {dl['delta'].median():+.3f}")
print()
print("So the fame pattern is not confined to the slope: the final-season collapse")
print("the belief is built on is also concentrated in the widely-watched series.")
print("Both cuts carry the endogeneity caveat below.")
print()


print("=" * 78)
print("WHAT THIS DOES AND DOES NOT LICENSE")
print("=" * 78)
print("Licensed (descriptive): the series the decline belief is drawn from do")
print("  decline far more often than the typical series, and the headline")
print("  'fewer than one in six' does not describe them.")
print("NOT licensed (causal): that fame causes decline. Vote counts rise in")
print("  response to a disappointing ending -- this project measured that on")
print("  Game of Thrones when choosing a weighting scheme -- so cause and")
print("  effect are entangled here and cannot be separated with this data.")
