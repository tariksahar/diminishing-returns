"""Phase 2 -- how much of the headline three-way split is estimation noise?

The headline (16.9% clear decline / 57.4% flat / 25.7% clear rise) sorts every
series by a fitted slope into bands cut at +/-0.5. But each slope is an ESTIMATE
with its own standard error, and a series near a cut-off can land on the wrong
side of it by luck. Nothing in the project had ever quantified that, even though
phase2_popularity.py already computes the standard errors for another purpose.

Two different questions, and they have opposite-looking answers, which is the
whole point of running this:

  1. Can we classify an INDIVIDUAL series confidently? Largely no -- a single
     series' slope is imprecise relative to a 0.5-point band.
  2. Is the POPULATION split distorted? Barely -- with 3,234 series, errors that
     scatter a series across a cut-off mostly cancel, and what remains is
     correctable.

Reporting only (1) would wrongly imply the headline is shaky; reporting only (2)
would hide that the per-series labels are soft. Both are printed.

Method for (2), in two steps of decreasing assumption-freedom:

  * How much noise is there? The observed variance of the slopes across series
    is the sum of the real between-series variance and the mean squared
    estimation error (errors are independent of the true values, so variances
    add). Subtracting gives the real spread. This needs no assumption about the
    SHAPE of either distribution and is the firmer of the two results.

  * What would the split be without noise? This needs a shape assumption, and
    the obvious tool is the wrong one. Empirical-Bayes shrinkage was used here
    first and it is a MISTAKE for this purpose: posterior means are deliberately
    over-shrunk as a set, so their variance is well below the true variance
    (checked below -- about 22% below), and counting how many fall past a fixed
    cut therefore understates both tails by construction. The same normal model
    read parametrically instead gives the OPPOSITE sign, and is rejected outright
    because it cannot reproduce the share we actually observe. Both traps are
    printed rather than hidden, because they are why the answer is stated the
    way it is.

    What is used instead: solve for the scale factor c such that, if the true
    slopes were the observed ones with their deviations from the mean shrunk by
    c, the EXPECTED share of noisy estimates past the cut equals the share we
    actually see. The expectation is exact -- mean of Phi((cut - t_i)/se_i) --
    so there is no simulation and no random seed. It assumes normal estimation
    ERROR, which every standard error and interval in the report already
    assumes, but nothing about the distribution of true slopes beyond its shape
    being preserved under scaling. Fitted on the decline share only, so the rise
    share it predicts is a genuine out-of-sample check.

Prints its findings; exports nothing, since no figure consumes it.
"""

import math

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")

CLEAR = 0.5  # the same clear-decline / clear-rise threshold as the headline

# ----------------------------------------------------------------------
# Refit every series, keeping the slope AND its standard error
# ----------------------------------------------------------------------
# Same weighted least squares as everywhere else in the project; the only
# addition is the SE, which needs the residuals the other scripts discard.
rows = []
for show_id, g in df.groupby("show_tconst"):
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
    # Weighted residual variance with the 2 fitted parameters taken out, then
    # the usual slope SE = sqrt(sigma^2 / S_xx).
    se = np.sqrt(((w * resid ** 2).sum() / (n - 2)) / s_xx)
    rows.append({"show_id": show_id, "n_ep": n, "slope": b, "se": se})

s = pd.DataFrame(rows)

# Cross-check against the stored table every other analysis reads, so this
# script cannot quietly be fitting something different.
stored = pd.read_json("data/processed/_phase2_slopes_full.json")
merged = stored.merge(s, on="show_id", suffixes=("_stored", "_here"))
assert len(merged) == len(stored), "show set differs from the stored slopes table"
assert np.allclose(merged["slope_stored"], merged["slope_here"], atol=1e-9), \
    "slopes disagree with data/processed/_phase2_slopes_full.json"
print(f"Refitted {len(s):,} series; slopes match the stored table exactly.")
print()

# ----------------------------------------------------------------------
# (1) HOW PRECISE IS ONE SERIES' SLOPE?
# ----------------------------------------------------------------------
print("=" * 78)
print("(1) PRECISION OF AN INDIVIDUAL SERIES' SLOPE")
print("=" * 78)
print(f"slope SE:  median {s['se'].median():.3f}   "
      f"IQR {s['se'].quantile(.25):.3f}-{s['se'].quantile(.75):.3f}   "
      f"90th pct {s['se'].quantile(.90):.3f}")
print()
print("Against a band half-width of 0.5, a typical SE of ~0.19 is not small.")
print()

dec = s["slope"] <= -CLEAR
ris = s["slope"] >= CLEAR

# A series is only confidently 'clear' if its whole 95% interval clears the cut.
amb_dec = int((dec & (s["slope"] + 1.96 * s["se"] > -CLEAR)).sum())
amb_ris = int((ris & (s["slope"] - 1.96 * s["se"] < CLEAR)).sum())
not_zero = int(((s["slope"].abs() - 1.96 * s["se"]) > 0).sum())

print(f"labelled 'clear decline': {int(dec.sum()):,}  of which {amb_dec:,} "
      f"({100*amb_dec/dec.sum():.0f}%) have a 95% CI still touching -0.5")
print(f"labelled 'clear rise':    {int(ris.sum()):,}  of which {amb_ris:,} "
      f"({100*amb_ris/ris.sum():.0f}%) have a 95% CI still touching +0.5")
print(f"series whose slope is distinguishable from zero at all: {not_zero:,} "
      f"({100*not_zero/len(s):.0f}%)")
print()
print("So a per-series label is soft: for most 'clear' series we can say the")
print("direction but not that the move certainly exceeds half a point. The bands")
print("are a reporting convention, not a claim about each individual series.")
print()

# ----------------------------------------------------------------------
# (2) IS THE POPULATION SPLIT DISTORTED?
# ----------------------------------------------------------------------
print("=" * 78)
print("(2) IS THE POPULATION SPLIT DISTORTED BY THAT NOISE?")
print("=" * 78)
var_obs = float(s["slope"].var(ddof=1))
var_err = float((s["se"] ** 2).mean())
var_true = var_obs - var_err
print(f"observed variance of slopes across series: {var_obs:.4f}")
print(f"  mean squared estimation error:           {var_err:.4f}  "
      f"({100*var_err/var_obs:.0f}% of it)")
print(f"  implied real between-series variance:    {var_true:.4f}")
print()
print("Only about a tenth of the spread between series is estimation noise, so")
print("the distribution the headline describes is mostly real differences.")
print()

slope = s["slope"].to_numpy(dtype=float)
se_v = s["se"].to_numpy(dtype=float)
mu = float(slope.mean())
obs_dec, obs_ris = float(dec.mean()), float(ris.mean())


def Phi(q):
    """Standard normal CDF, vectorised, without a scipy dependency."""
    return 0.5 * (1.0 + np.vectorize(math.erf)(q / math.sqrt(2.0)))


def expected_observed(true_vals, cut, upper=False):
    """Expected share of noisy ESTIMATES past `cut`, given true values and SEs.

    Exact under normal estimation error, which is what the SEs already assume.
    No simulation, so this is reproducible without a seed."""
    if upper:
        return float((1.0 - Phi((cut - true_vals) / se_v)).mean())
    return float(Phi((cut - true_vals) / se_v).mean())


# --- the two traps, printed rather than hidden -------------------------------
print("Two tempting corrections that are WRONG here, and why:")

shrunk = mu + (var_true / (var_true + se_v ** 2)) * (slope - mu)
var_shrunk = float(shrunk.var(ddof=1))
print(f"  (a) empirical-Bayes shrinkage. var(shrunk) = {var_shrunk:.4f} against a")
print(f"      true variance of {var_true:.4f}, i.e. {100*(1-var_shrunk/var_true):.0f}% too narrow. "
      "Posterior means are")
print("      over-shrunk AS A SET by design, so counting them past a fixed cut")
print(f"      understates both tails. It would report "
      f"{100*(shrunk <= -CLEAR).mean():.1f}% decline -- too low.")

sd_true, sd_obs = math.sqrt(var_true), math.sqrt(var_true + var_err)
par_dec = 100 * float(Phi(np.array([(-CLEAR - mu) / sd_true]))[0])
norm_pred_obs = 100 * float(Phi(np.array([(-CLEAR - mu) / sd_obs]))[0])
print(f"  (b) the same normal model read parametrically: true ~ N({mu:.3f}, {var_true:.3f})")
print(f"      gives {par_dec:.1f}% decline -- HIGHER than the observed "
      f"{100*obs_dec:.1f}%, the opposite sign.")
print(f"      It is rejected outright: that model predicts an OBSERVED share of")
print(f"      {norm_pred_obs:.1f}%, while we observe {100*obs_dec:.1f}%. It cannot reproduce")
print("      the data it is fitted to.")

z = (slope - mu) / math.sqrt(var_obs)
skew = float((z ** 3).mean())
ex_kurt = float((z ** 4).mean() - 3.0)
tail4 = 100 * float((np.abs(z) > 4).mean())
print(f"      Why: the slopes are skewed ({skew:+.2f}) and fat-tailed (excess "
      f"kurtosis {ex_kurt:+.2f});")
print(f"      {tail4:.2f}% sit beyond 4 SD against 0.006% under a normal, ~{tail4/0.0063:.0f}x too many.")
print()

# --- the correction actually used --------------------------------------------
lo, hi = 0.5, 1.0
for _ in range(80):
    c = (lo + hi) / 2
    if expected_observed(mu + c * (slope - mu), -CLEAR) > obs_dec:
        hi = c
    else:
        lo = c
c = (lo + hi) / 2
true_hat = mu + c * (slope - mu)

d_corr = 100 * float((true_hat <= -CLEAR).mean())
r_corr = 100 * float((true_hat >= CLEAR).mean())

print(f"Scale-family deconvolution: c = {c:.4f}")
print(f"  reproduces the fitted decline share: "
      f"{100*expected_observed(true_hat, -CLEAR):.2f}% vs {100*obs_dec:.2f}% observed")
print(f"  predicts a rise share of {100*expected_observed(true_hat, CLEAR, upper=True):.2f}% "
      f"against {100*obs_ris:.2f}% observed --")
print("  not fitted, so that agreement is a real out-of-sample check.")
print()
print(f"{'':<28}{'decline':>10}{'flat':>10}{'rise':>10}")
print(f"  {'as published':<26}{100*obs_dec:>9.1f}%"
      f"{100*(1-obs_dec-obs_ris):>9.1f}%{100*obs_ris:>9.1f}%")
print(f"  {'noise removed':<26}{d_corr:>9.1f}%{100-d_corr-r_corr:>9.1f}%{r_corr:>9.1f}%")
print()
print(f"The correction is about {abs(d_corr - 100*obs_dec):.1f} of a percentage point on the")
print("decline share, and it points the way that strengthens the published")
print("conclusion. The DIRECTION is the robust part, and it does not rest on the")
print("deconvolution: noise smooths a density that is peaked inside the middle")
print("band, so mass necessarily flows outward across the band's two edges. The")
print("check above shows it directly -- feeding the estimates back in as if they")
print(f"were the truth predicts {100*expected_observed(slope, -CLEAR):.1f}% observed decline "
      f"against the {100*obs_dec:.1f}% we see.")
print()
print("Bottom line: the headline survives its own estimation error, with about a")
print("point of slack in its favour. The MAGNITUDE carries a shape assumption and")
print("should not be leaned on harder than that.")
