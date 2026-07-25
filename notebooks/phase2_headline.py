"""The report's headline number: of all 3,234 shows, what share trend down
vs up? Recompute the sqrt(votes)-weighted slope FRESH from the parquet (do
not trust the prior-session slopes file), report the split, and cross-check
against that old file to confirm they agree."""

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")


def weighted_slope(x, y, w):
    W = np.sum(w)
    x_bar = np.sum(w * x) / W
    y_bar = np.sum(w * y) / W
    return np.sum(w * (x - x_bar) * (y - y_bar)) / np.sum(w * (x - x_bar) ** 2)


rows = []
for show_id, g in df.groupby("show_tconst"):
    g = g.sort_values("overall_order")
    n = len(g)
    x = (g["overall_order"].to_numpy(float) - 1) / (n - 1)
    y = g["average_rating"].to_numpy(float)
    w = np.sqrt(g["num_votes"].to_numpy(float))
    rows.append({"show_id": show_id, "ongoing": bool(g["ongoing"].iloc[0]),
                 "slope": weighted_slope(x, y, w)})
r = pd.DataFrame(rows)


def report(sub, label):
    n = len(sub)
    down = (sub["slope"] < 0).mean() * 100
    up = (sub["slope"] > 0).mean() * 100
    clear_down = (sub["slope"] <= -0.5).mean() * 100
    clear_up = (sub["slope"] >= 0.5).mean() * 100
    flat = ((sub["slope"] > -0.5) & (sub["slope"] < 0.5)).mean() * 100
    print(f"\n--- {label} (n={n:,}) ---")
    print(f"  median slope: {sub['slope'].median():+.3f}   mean: {sub['slope'].mean():+.3f}")
    print(f"  trending down at all (slope < 0): {down:.1f}%")
    print(f"  trending up at all   (slope > 0): {up:.1f}%")
    print(f"  CLEAR decline (<= -0.5 points start-to-end): {clear_down:.1f}%")
    print(f"  ROUGHLY FLAT  (between -0.5 and +0.5):       {flat:.1f}%")
    print(f"  CLEAR rise    (>= +0.5):                     {clear_up:.1f}%")


report(r, "ALL SHOWS")
report(r[~r["ongoing"]], "ENDED SHOWS ONLY")

# Cross-check against the prior-session slopes file.
try:
    old = pd.read_json("data/processed/_phase2_slopes_full.json")[["show_id", "slope"]]
    m = r.merge(old, on="show_id", suffixes=("_fresh", "_old"))
    diff = (m["slope_fresh"] - m["slope_old"]).abs()
    print(f"\n--- VERIFICATION against the stored slopes file (n={len(m):,}) ---")
    print(f"  max abs difference: {diff.max():.6f}   mean difference: {diff.mean():.6f}")
    print("  -> ~0 confirms the stored file also used sqrt(votes) and is consistent")
except Exception as e:
    print("Cross-check against the stored file skipped:", e)
