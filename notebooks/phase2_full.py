"""Phase 2 -- full-dataset run: compute the sqrt(num_votes)-weighted trend
slope for all 3,234 shows (the decided methodology from docs/decisions.md),
and summarize the overall decline/rise picture."""

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


records = []
for show_id, g in df.groupby("show_tconst"):
    g = g.sort_values("overall_order")
    n = len(g)
    y = g["average_rating"].to_numpy(dtype=float)
    v = g["num_votes"].to_numpy(dtype=float)
    x = (g["overall_order"].to_numpy(dtype=float) - 1) / (n - 1)
    a, b = weighted_fit(x, y, np.sqrt(v))
    records.append({
        "show_id": show_id,
        "title": g["show_title"].iloc[0],
        "n_ep": n,
        "n_season": int(g["season_number"].nunique()),
        "total_votes": int(v.sum()),
        "mean_rating": float(y.mean()),
        "slope": float(b),
        "ongoing": bool(g["ongoing"].iloc[0]),
        "start_year": int(g["start_year"].iloc[0]) if pd.notna(g["start_year"].iloc[0]) else None,
    })

res = pd.DataFrame(records)
print(f"Total shows: {len(res):,}")
print()

declining = (res["slope"] < 0).sum()
rising = (res["slope"] > 0).sum()
flat = (res["slope"] == 0).sum()
print("=== OVERALL PICTURE (sqrt(votes)-weighted slope) ===")
print(f"declining (slope < 0): {declining:,}  ({100*declining/len(res):.1f}%)")
print(f"rising    (slope > 0): {rising:,}  ({100*rising/len(res):.1f}%)")
print(f"exactly flat (slope = 0): {flat:,}")
print()

print("=== SLOPE DISTRIBUTION ===")
print(res["slope"].describe())
print()
print("Percentiles:")
print(res["slope"].quantile([0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]))
print()

strong_dec = (res["slope"] <= -0.5).sum()
mild_dec = ((res["slope"] < 0) & (res["slope"] > -0.5)).sum()
mild_ris = ((res["slope"] > 0) & (res["slope"] < 0.5)).sum()
strong_ris = (res["slope"] >= 0.5).sum()
print("=== THRESHOLD-BASED CLASSIFICATION ===")
print(f"clear decline (slope <= -0.5):   {strong_dec:,}  ({100*strong_dec/len(res):.1f}%)")
print(f"mild decline  (-0.5 < slope < 0): {mild_dec:,}  ({100*mild_dec/len(res):.1f}%)")
print(f"mild rise     (0 < slope < 0.5):  {mild_ris:,}  ({100*mild_ris/len(res):.1f}%)")
print(f"clear rise    (slope >= 0.5):     {strong_ris:,}  ({100*strong_ris/len(res):.1f}%)")
print()

print("=== ONGOING vs ENDED ===")
for flag, label in [(False, "ended  "), (True, "ongoing")]:
    sub = res[res["ongoing"] == flag]
    print(f"{label}: n={len(sub):,}  mean slope={sub['slope'].mean():+.3f}  "
          f"median slope={sub['slope'].median():+.3f}  declining={100*(sub['slope']<0).mean():.1f}%")
print()

print("=== 15 STEEPEST DECLINES (min 5,000 total votes) ===")
sub = res[res["total_votes"] >= 5000].sort_values("slope")
for _, r in sub.head(15).iterrows():
    print(f"  {r['title']:<35} slope={r['slope']:+.2f}  ({r['n_ep']} episodes, {r['n_season']} seasons, {r['start_year']})")
print()

print("=== 15 STRONGEST RISES (min 5,000 total votes) ===")
for _, r in sub.sort_values("slope", ascending=False).head(15).iterrows():
    print(f"  {r['title']:<35} slope={r['slope']:+.2f}  ({r['n_ep']} episodes, {r['n_season']} seasons, {r['start_year']})")
print()

# Save the full table for downstream use (final-season analysis, figures).
res.to_json("data/processed/_phase2_slopes_full.json", orient="records")
print("Saved: data/processed/_phase2_slopes_full.json")

# Histogram bins for a figure.
counts, edges = np.histogram(res["slope"].clip(-4, 4), bins=40)
hist = {"counts": counts.tolist(), "edges": [round(float(e), 3) for e in edges]}
with open("data/processed/_phase2_hist.json", "w", encoding="utf-8") as f:
    json.dump({
        "hist": hist,
        "n_shows": int(len(res)),
        "declining_pct": round(100*declining/len(res), 1),
        "rising_pct": round(100*rising/len(res), 1),
        "mean_slope": round(float(res["slope"].mean()), 3),
        "median_slope": round(float(res["slope"].median()), 3),
    }, f)
print("Saved: data/processed/_phase2_hist.json")
