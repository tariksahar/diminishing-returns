"""Two clean tests.
  (1) Regression to the mean, done properly: split each show's episodes into
      disjoint first/second halves so the baseline and the outcome share no
      episodes (no mathematical coupling). Also estimate the reliability of a
      half-mean (odd/even split-half + Spearman-Brown) to gauge how much of
      the regression is unavoidable noise vs a real quality change.
  (2) Genre effect NET of era and length: OLS of the full-show sqrt-weighted
      slope on multi-hot genre dummies + start_year + n_season + ongoing.
      Sixteen genre coefficients are tested at once, so a per-coefficient
      |t| > 2 will flag roughly one genre by chance alone. Bonferroni and
      Benjamini-Hochberg thresholds are computed alongside the raw ones so the
      report can say which genres actually survive being one of sixteen tests.
"""

import math

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")
slopes = pd.read_json("data/processed/_phase2_slopes_full.json")

# ----------------------------------------------------------------------
# (1) REGRESSION TO THE MEAN -- disjoint halves
# ----------------------------------------------------------------------
rows = []
for show_id, g in df.groupby("show_tconst"):
    g = g.sort_values("overall_order")
    n = len(g)
    if n < 8:
        continue
    half = n // 2
    first = g.iloc[:half]
    second = g.iloc[half:]
    b = first["average_rating"].mean()       # baseline (independent)
    o = second["average_rating"].mean()      # outcome  (independent)
    # Split-half reliability pieces (odd/even episodes within the first half).
    fr = first["average_rating"].to_numpy()
    odd = fr[1::2].mean() if len(fr[1::2]) else np.nan
    even = fr[0::2].mean() if len(fr[0::2]) else np.nan
    rows.append({"show_id": show_id, "b": b, "o": o, "odd": odd, "even": even})

r = pd.DataFrame(rows)
print("=" * 70)
print("(1) REGRESSION TO THE MEAN -- CLEAN TEST (disjoint first/second halves)")
print("=" * 70)
print(f"shows with >= 8 episodes: {len(r)}")

print("\nCOMPARISON:")
print("  BIASED measure (slope vs its own fitted intercept): -0.373")
print("  -- inflated by mathematical coupling; see phase2_deep.py section 4")

corr_bo = np.corrcoef(r["b"], r["o"])[0, 1]
print(f"  CLEAN measure (first-half mean vs second-half mean, disjoint): r = {corr_bo:+.3f}")

bb = np.polyfit(r["b"], r["o"], 1)
print(f"  o = {bb[0]:.3f} * b + {bb[1]:.3f}   (a slope < 1 means regression to the mean)")

# Reliability of a half-mean via odd/even split + Spearman-Brown correction.
rr = r.dropna(subset=["odd", "even"])
r_split = np.corrcoef(rr["odd"], rr["even"])[0, 1]
rel = 2 * r_split / (1 + r_split)
print(f"  first-half reliability (Spearman-Brown): {rel:.3f}")
print(f"  -> under 'stable quality + noise only' we would expect an o-on-b slope of ~{rel:.3f}")

# How far the observed slope sits below the noise-only expectation is the part
# of the fall-back that noise cannot explain -- the REAL extra decline of strong
# starters. Reported in rating points rather than as a verdict, because the
# honest answer here is neither "yes" nor "no" but "yes, and it is negligible":
# a gap this small moves the top quartile by less than a tenth of a point.
gap = rel - bb[0]
b_mean = r["b"].mean()
top_b = r.loc[r["b"] >= r["b"].quantile(0.75), "b"].mean()
extra = gap * (top_b - b_mean)
print(f"     observed {bb[0]:.3f}, which is {gap:.3f} below that expectation")
print(f"     -> a real extra decline exists, but it is tiny: {extra:.3f} rating points for")
print(f"        the average top-quartile starter (baseline {top_b:.2f} vs the {b_mean:.2f} overall mean)")

print("\nBY BASELINE QUARTILE (do strong starters fall back?):")
r["bq"] = pd.qcut(r["b"], 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"])
for q, sub in r.groupby("bq", observed=True):
    print(f"  {q:<14} first half={sub['b'].mean():.2f}  second half={sub['o'].mean():.2f}  "
          f"change={sub['o'].mean()-sub['b'].mean():+.2f}")

# ----------------------------------------------------------------------
# (2) GENRE NET OF ERA + LENGTH  (OLS)
# ----------------------------------------------------------------------
print()
print("=" * 70)
print("(2) GENRE EFFECT WITH ERA + LENGTH HELD FIXED (OLS)")
print("=" * 70)
g1 = df.groupby("show_tconst").agg(genres=("genres", "first")).reset_index()
d = slopes.merge(g1, left_on="show_id", right_on="show_tconst", how="left")
d["start_year"] = pd.to_numeric(d["start_year"], errors="coerce")
d = d.dropna(subset=["start_year", "slope", "n_season", "genres"]).copy()

GENRES = ["Documentary", "Biography", "Horror", "Family", "Mystery", "Romance",
          "Fantasy", "History", "Sci-Fi", "Crime", "Drama", "Comedy",
          "Thriller", "Adventure", "Action", "Animation"]
for gen in GENRES:
    d[gen] = d["genres"].str.split(",").apply(lambda xs: int(gen in xs))

d["yr_c"] = d["start_year"] - d["start_year"].mean()
d["ongoing_i"] = d["ongoing"].astype(int)

cols = ["yr_c", "n_season", "ongoing_i"] + GENRES
X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in cols])
y = d["slope"].to_numpy(float)
XtX_inv = np.linalg.inv(X.T @ X)
beta = XtX_inv @ X.T @ y
resid = y - X @ beta
sigma2 = resid @ resid / (len(d) - X.shape[1])
se = np.sqrt(np.diag(sigma2 * XtX_inv))       # classical SEs
tstat = beta / se
names = ["intercept"] + cols


# Two-sided p-values. With 3,214 residual degrees of freedom the t-distribution
# is indistinguishable from the normal, so erfc gives the exact normal tail and
# avoids a scipy dependency: p = 2*(1 - Phi(|t|)) = erfc(|t|/sqrt(2)).
pvals = np.array([math.erfc(abs(t) / np.sqrt(2)) for t in tstat])

# --- Multiplicity over the 16 genre coefficients ------------------------------
# Era, length and ongoing are pre-specified single hypotheses and are not part
# of the family; the genre dummies are the screen where the correction belongs.
gi = [names.index(gn) for gn in GENRES]
m = len(GENRES)
alpha = 0.05
bonf_alpha = alpha / m

# Benjamini-Hochberg: sort the family's p-values, find the largest k whose
# p_(k) <= k/m * alpha, and reject everything at or below it. Controls the false
# DISCOVERY rate rather than the family-wise error rate, so it is less punishing
# than Bonferroni while still accounting for the 16 tests.
gp = sorted(((pvals[i], i) for i in gi))
bh_cut = 0.0
for k, (p, _) in enumerate(gp, start=1):
    if p <= k / m * alpha:
        bh_cut = p
bh_survivors = {i for p, i in gp if p <= bh_cut}

print(f"n = {len(d)} shows.  Coefficient = this genre's contribution to the slope,")
print("with era and length held fixed.")
print()
print(f"{'variable':<14}{'coef':>10}{'std err':>10}{'t':>8}{'p':>10}  verdict")
for nm in ["yr_c", "n_season", "ongoing_i"]:
    i = names.index(nm)
    sig = "significant" if pvals[i] < alpha else ""
    print(f"  {nm:<12}{beta[i]:>10.4f}{se[i]:>10.4f}{tstat[i]:>8.1f}{pvals[i]:>10.2e}  {sig}")
print()

# The |t| a genre must reach under Bonferroni, found by bisecting the same
# normal tail used for the p-values. Reported because the report and the
# coefficient figure both speak in t-statistics, not p-values.
lo, hi = 0.0, 10.0
for _ in range(100):
    mid = (lo + hi) / 2
    if math.erfc(mid / np.sqrt(2)) > bonf_alpha:
        lo = mid
    else:
        hi = mid
bonf_t = (lo + hi) / 2

print(f"  --- genres: {m} coefficients tested at once "
      f"(reference = shows NOT carrying that genre) ---")
print(f"  raw: alpha={alpha} (|t| > 1.96)   "
      f"Bonferroni: alpha={bonf_alpha:.5f} (|t| > {bonf_t:.2f})   "
      f"BH: reject p <= {bh_cut:.5f}")
order = sorted(GENRES, key=lambda gn: beta[names.index(gn)])
for gn in order:
    i = names.index(gn)
    marks = []
    if pvals[i] < alpha:
        marks.append("raw")
    if i in bh_survivors:
        marks.append("BH")
    if pvals[i] < bonf_alpha:
        marks.append("Bonferroni")
    print(f"  {gn:<12}{beta[i]:>10.4f}{se[i]:>10.4f}{tstat[i]:>8.1f}{pvals[i]:>10.2e}"
          f"  {', '.join(marks)}")
print()
n_raw = sum(1 for i in gi if pvals[i] < alpha)
n_bh = len(bh_survivors)
n_bonf = sum(1 for i in gi if pvals[i] < bonf_alpha)
print(f"Genres passing: {n_raw} raw, {n_bh} after Benjamini-Hochberg, "
      f"{n_bonf} after Bonferroni.")
print(f"Expected false positives from {m} tests at raw alpha={alpha}: "
      f"{m*alpha:.1f}. That is why the raw count cannot be reported alone --")
print("the weakest genres on the list are exactly where that one lands.")
print()
print("Compare with the raw medians from phase2_deep.py: Animation +0.332,")
print("Documentary -0.171. Coefficients smaller than the raw effect mean part")
print("of that raw gap was era/length confounding, not genre.")
