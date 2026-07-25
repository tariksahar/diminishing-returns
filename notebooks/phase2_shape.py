"""Phase 2 -- C: trajectory shape.
  1. Best-season location: which season (as a fraction of the show's total
     seasons) has the highest mean rating? Is there a common 'peak season'
     (e.g. a 'sophomore surge' at season 2)?
  2. Curvature: fit a sqrt(votes)-weighted QUADRATIC trend
     (rating ~ a + b*x + c*x^2, x = normalized episode order) per show.
     c < 0 with an interior vertex = 'jumped the shark' (rises then falls).
     c > 0 with an interior vertex = 'found itself' (dips then recovers).
  3. Volatility: weighted RMSE of the LINEAR fit's residuals -- how bumpy a
     show is beyond its basic trend.
All weighting uses sqrt(num_votes), consistent with the decided methodology.

NOTE: the per-season-count breakdown in phase2_peak_location.py shows the
'season 2 peak' seen below is an artifact of how many shows are short; read
the two together.
"""

import json

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")
show_votes = df.groupby("show_tconst")["num_votes"].sum()


def weighted_linear(x, y, w):
    W = np.sum(w)
    x_bar = np.sum(w * x) / W
    y_bar = np.sum(w * y) / W
    b = np.sum(w * (x - x_bar) * (y - y_bar)) / np.sum(w * (x - x_bar) ** 2)
    a = y_bar - b * x_bar
    return a, b


def weighted_quad(x, y, w):
    X = np.column_stack([np.ones_like(x), x, x**2])
    sw = np.sqrt(w)
    Xw = X * sw[:, None]
    yw = y * sw
    coef, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    return coef  # a, b, c  (y = a + b*x + c*x^2)


rows = []
best_season_rows = []

for show_id, g in df.groupby("show_tconst"):
    g = g.sort_values("overall_order")
    n = len(g)
    n_season = g["season_number"].nunique()
    x = (g["overall_order"].to_numpy(dtype=float) - 1) / (n - 1)
    y = g["average_rating"].to_numpy(dtype=float)
    v = g["num_votes"].to_numpy(dtype=float)
    w = np.sqrt(v)

    a_lin, b_lin = weighted_linear(x, y, w)
    pred_lin = a_lin + b_lin * x
    resid = y - pred_lin
    rmse = np.sqrt(np.sum(w * resid**2) / np.sum(w))

    a_q, b_q, c_q = weighted_quad(x, y, w)
    vertex = -b_q / (2 * c_q) if abs(c_q) > 1e-6 else None

    shape = "linear/flat"
    if vertex is not None and 0.15 <= vertex <= 0.85:
        if c_q < -0.05:
            shape = "jumped_the_shark"  # peaks in the middle then falls
        elif c_q > 0.05:
            shape = "found_itself"      # dips in the middle then recovers

    rows.append({
        "show_id": show_id, "title": g["show_title"].iloc[0],
        "n_ep": n, "n_season": int(n_season),
        "total_votes": int(v.sum()),
        "curvature": float(c_q), "vertex": float(vertex) if vertex is not None else None,
        "shape": shape, "rmse": float(rmse), "slope": float(b_lin),
    })

    # Best-season location within this show.
    season_means = g.groupby("season_number")["average_rating"].mean()
    ranked_seasons = sorted(season_means.index)
    best_season = season_means.idxmax()
    rank = ranked_seasons.index(best_season) + 1  # 1-indexed rank among this show's seasons
    frac = (rank - 1) / (n_season - 1) if n_season > 1 else 0.5
    best_season_rows.append({
        "show_id": show_id, "n_season": int(n_season),
        "best_rank": rank, "best_frac": frac,
    })

res = pd.DataFrame(rows)
bs = pd.DataFrame(best_season_rows)

print("=" * 60)
print("1. WHERE IS THE BEST SEASON?")
print("=" * 60)
print("best_frac distribution across all shows (0 = first season, 1 = last):")
print(bs["best_frac"].describe())
print()
print(f"  best season is the FIRST season: {100*(bs['best_rank']==1).mean():.1f}%")
print(f"  best season is the LAST season:  "
      f"{100*(bs.apply(lambda r: r['best_rank']==r['n_season'], axis=1)).mean():.1f}%")
print()
print("Best-season distribution among 3-season shows (sophomore-surge test):")
three = bs[bs["n_season"] == 3]
print(three["best_rank"].value_counts(normalize=True).sort_index() * 100)
print()
print("Best-season distribution among 4-season shows:")
four = bs[bs["n_season"] == 4]
print(four["best_rank"].value_counts(normalize=True).sort_index() * 100)
print()
print("Best-season distribution among 5-season shows:")
five = bs[bs["n_season"] == 5]
print(five["best_rank"].value_counts(normalize=True).sort_index() * 100)
print()

print("=" * 60)
print("2. CURVATURE / TRAJECTORY SHAPE")
print("=" * 60)
print(res["shape"].value_counts())
print(res["shape"].value_counts(normalize=True) * 100)
print()
pop = res[res["total_votes"] >= 20000]
print("Clearest 'JUMPED THE SHARK' cases (min 20k votes, most negative curvature):")
jts = pop[pop["shape"] == "jumped_the_shark"].sort_values("curvature")
for _, r in jts.head(12).iterrows():
    print(f"  {r['title']:<32} vertex={r['vertex']:.2f}  curvature={r['curvature']:.2f}")
print()
print("Clearest 'FOUND ITSELF' cases (min 20k votes, most positive curvature):")
fi = pop[pop["shape"] == "found_itself"].sort_values("curvature", ascending=False)
for _, r in fi.head(12).iterrows():
    print(f"  {r['title']:<32} vertex={r['vertex']:.2f}  curvature={r['curvature']:.2f}")
print()

print("=" * 60)
print("3. VOLATILITY")
print("=" * 60)
print(res["rmse"].describe())
print()
print("12 most volatile shows (min 20k votes):")
for _, r in pop.sort_values("rmse", ascending=False).head(12).iterrows():
    print(f"  {r['title']:<32} rmse={r['rmse']:.2f}  n_ep={r['n_ep']}")
print()
print("12 most consistent shows (min 20k votes):")
for _, r in pop.sort_values("rmse").head(12).iterrows():
    print(f"  {r['title']:<32} rmse={r['rmse']:.2f}  n_ep={r['n_ep']}")

res.to_json("data/processed/_phase2_shape_full.json", orient="records")
out = {
    "shape_counts": res["shape"].value_counts().to_dict(),
    "best_frac_median": round(float(bs["best_frac"].median()), 3),
    "pct_first_best": round(100*float((bs['best_rank']==1).mean()), 1),
    "pct_last_best": round(100*float((bs.apply(lambda r: r['best_rank']==r['n_season'], axis=1)).mean()), 1),
}
with open("data/processed/_phase2_shape_summary.json", "w", encoding="utf-8") as f:
    json.dump(out, f)
print()
print("Saved: _phase2_shape_full.json, _phase2_shape_summary.json")
