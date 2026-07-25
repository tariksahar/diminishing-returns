"""Phase 2 -- deeper cuts on the sqrt(votes)-weighted per-show slope:
by genre, by era (start decade), by length (episodes/seasons), and by the
show's own baseline rating. Prints tables and saves JSON for the report.

IMPORTANT: these are RAW cuts with no controls. Two follow-ups correct them:
  - phase2_era_disentangle.py: era, length and ongoing status are tangled
    together, so the raw era table overstates a standalone era effect.
  - phase2_rtm_genre.py: section 4 below is BIASED (see the warning printed
    there) and the genre table is re-run with era/length held fixed.
Read this script together with those two, not on its own.
"""

import json

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")


def weighted_fit(x, y, w):
    W = np.sum(w)
    x_bar = np.sum(w * x) / W
    y_bar = np.sum(w * y) / W
    b = np.sum(w * (x - x_bar) * (y - y_bar)) / np.sum(w * (x - x_bar) ** 2)
    a = y_bar - b * x_bar
    return a, b


rows = []
for show_id, g in df.groupby("show_tconst"):
    g = g.sort_values("overall_order")
    n = len(g)
    y = g["average_rating"].to_numpy(dtype=float)
    v = g["num_votes"].to_numpy(dtype=float)
    x = (g["overall_order"].to_numpy(dtype=float) - 1) / (n - 1)
    a, b = weighted_fit(x, y, np.sqrt(v))
    rows.append({
        "show_id": show_id,
        "title": g["show_title"].iloc[0],
        "genres": g["genres"].iloc[0],
        "n_ep": n,
        "n_season": int(g["season_number"].nunique()),
        "start_year": g["start_year"].iloc[0],
        "mean_rating": float(y.mean()),
        "first_ep": float(y[0]),
        "predicted_start": float(a),          # trend value at x=0
        "predicted_end": float(a + b),        # trend value at x=1
        "slope": float(b),
        "ongoing": bool(g["ongoing"].iloc[0]),
    })

res = pd.DataFrame(rows)
res["start_year"] = pd.to_numeric(res["start_year"], errors="coerce")


def summarize(sub):
    return pd.Series({
        "n": len(sub),
        "mean_slope": sub["slope"].mean(),
        "median_slope": sub["slope"].median(),
        "pct_declining": 100 * (sub["slope"] < 0).mean(),
    })


print("=" * 64)
print("1. BY GENRE (a show can carry several genres -> exploded)")
print("=" * 64)
exploded = res.assign(genre=res["genres"].str.split(",")).explode("genre")
gstats = exploded.groupby("genre").apply(summarize, include_groups=False)
gstats = gstats[gstats["n"] >= 30].sort_values("median_slope")
for genre, r in gstats.iterrows():
    print(f"  {genre:<14} n={int(r['n']):>4}  median slope={r['median_slope']:+.3f}  "
          f"mean={r['mean_slope']:+.3f}  declining={r['pct_declining']:.0f}%")

print()
print("=" * 64)
print("2. BY ERA (premiere decade)")
print("=" * 64)
res["decade"] = (res["start_year"] // 10 * 10)
dstats = res[res["start_year"].notna()].groupby("decade").apply(summarize, include_groups=False)
dstats = dstats[dstats["n"] >= 15]
for dec, r in dstats.iterrows():
    print(f"  {int(dec)}s  n={int(r['n']):>4}  median slope={r['median_slope']:+.3f}  "
          f"mean={r['mean_slope']:+.3f}  declining={r['pct_declining']:.0f}%")

print()
print("=" * 64)
print("3. BY LENGTH (episode-count band)")
print("=" * 64)
res["ep_bin"] = pd.cut(res["n_ep"], bins=[0, 25, 50, 100, 10000],
                       labels=["13-25", "26-50", "51-100", "100+"])
for b, sub in res.groupby("ep_bin", observed=True):
    r = summarize(sub)
    print(f"  {b:<8} n={int(r['n']):>4}  median slope={r['median_slope']:+.3f}  "
          f"mean={r['mean_slope']:+.3f}  declining={r['pct_declining']:.0f}%")
print()
print("   by season count:")
res["season_bin"] = pd.cut(res["n_season"], bins=[0, 2, 3, 5, 100],
                           labels=["2", "3", "4-5", "6+"])
for b, sub in res.groupby("season_bin", observed=True):
    r = summarize(sub)
    print(f"  {b:<8} n={int(r['n']):>4}  median slope={r['median_slope']:+.3f}  "
          f"mean={r['mean_slope']:+.3f}  declining={r['pct_declining']:.0f}%")

print()
print("=" * 64)
print("4. BY BASELINE RATING -- BIASED, DO NOT QUOTE")
print("=" * 64)
print("  WARNING: correlating the slope with the SAME fit's intercept couples")
print("  the two through shared noise and manufactures a negative relationship.")
print("  The number below is kept only to document the trap. The unbiased")
print("  disjoint-halves test lives in phase2_rtm_genre.py and shows the real")
print("  effect is nearly negligible (~0.07 rating points).")
print()
corr = np.corrcoef(res["predicted_start"], res["slope"])[0, 1]
print(f"  (biased) correlation of trend start with slope: {corr:+.3f}")
print()
res["start_bin"] = pd.cut(res["predicted_start"], bins=[0, 7, 7.5, 8, 8.5, 11],
                          labels=["<7.0", "7.0-7.5", "7.5-8.0", "8.0-8.5", "8.5+"])
for b, sub in res.groupby("start_bin", observed=True):
    r = summarize(sub)
    print(f"  start {b:<9} n={int(r['n']):>4}  median slope={r['median_slope']:+.3f}  "
          f"declining={r['pct_declining']:.0f}%")

out = {
    "genre": [{"genre": g, "n": int(r["n"]), "median_slope": round(r["median_slope"], 3),
               "mean_slope": round(r["mean_slope"], 3), "pct_declining": round(r["pct_declining"], 1)}
              for g, r in gstats.iterrows()],
    "decade": [{"decade": int(d), "n": int(r["n"]), "median_slope": round(r["median_slope"], 3),
                "pct_declining": round(r["pct_declining"], 1)} for d, r in dstats.iterrows()],
    "start_corr_biased": round(float(corr), 3),
}
with open("data/processed/_phase2_deep.json", "w", encoding="utf-8") as f:
    json.dump(out, f)
print()
print("Saved: data/processed/_phase2_deep.json")
