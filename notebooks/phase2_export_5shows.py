"""Export episode-level data + two weighted trend lines (linear num_votes vs
sqrt(num_votes)) for 5 specific shows, for a visual side-by-side comparison."""

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


wanted = ["Game of Thrones", "Lost", "Chuck", "Breaking Bad", "Monk"]

result = {}
for name in wanted:
    sub = df[df["show_title"] == name]
    if len(sub) == 0:
        print(f"MISSING: {name}")
        continue
    show_id = sub.groupby("show_tconst")["num_votes"].sum().idxmax()
    g = df[df["show_tconst"] == show_id].sort_values("overall_order")
    n = len(g)
    x = (g["overall_order"].to_numpy(dtype=float) - 1) / (n - 1)
    y = g["average_rating"].to_numpy(dtype=float)
    v = g["num_votes"].to_numpy(dtype=float)

    a_lin, b_lin = weighted_fit(x, y, v)
    a_sqrt, b_sqrt = weighted_fit(x, y, np.sqrt(v))
    a_none, b_none = weighted_fit(x, y, np.ones_like(v))

    print(f"{name:<18} n_ep={n:<4} unweighted={b_none:+.2f}  sqrt={b_sqrt:+.2f}  linear={b_lin:+.2f}")

    result[name] = {
        "n_ep": int(n),
        "n_season": int(g["season_number"].nunique()),
        "episodes": [
            {
                "x": round(float(xi), 4),
                "rating": round(float(ri), 1),
                "votes": int(vi),
                "season": int(si),
            }
            for xi, ri, vi, si in zip(x, y, v, g["season_number"])
        ],
        "fit_linear": {"a": round(float(a_lin), 4), "b": round(float(b_lin), 4)},
        "fit_sqrt": {"a": round(float(a_sqrt), 4), "b": round(float(b_sqrt), 4)},
        "fit_none": {"a": round(float(a_none), 4), "b": round(float(b_none), 4)},
    }

out_path = "data/processed/_phase2_5shows.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f)
print(f"\nWrote {out_path}")
