"""Compare 4 weighting schemes (none, num_votes, sqrt(num_votes), log(num_votes))
on real shows: fit rating ~ normalized_episode_position with each weight and
report the resulting slope, to make the abstract tradeoff concrete."""

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")


def weighted_slope(x, y, w):
    """Weighted least squares slope for y = a + b*x, weights w."""
    W = np.sum(w)
    x_bar = np.sum(w * x) / W
    y_bar = np.sum(w * y) / W
    b = np.sum(w * (x - x_bar) * (y - y_bar)) / np.sum(w * (x - x_bar) ** 2)
    return b


examples = ["Friends", "Game of Thrones", "Breaking Bad", "The Sopranos", "Dexter"]

print(f"{'Show':<20}{'unweighted':>12}{'num_votes':>12}{'sqrt(votes)':>14}{'log(votes)':>12}")
for name in examples:
    sub = df[df["show_title"] == name]
    if len(sub) == 0:
        continue
    show_id = sub.groupby("show_tconst")["num_votes"].sum().idxmax()
    g = sub[sub["show_tconst"] == show_id].sort_values("overall_order")
    n = len(g)
    x = (g["overall_order"].to_numpy(dtype=float) - 1) / (n - 1)
    y = g["average_rating"].to_numpy(dtype=float)
    v = g["num_votes"].to_numpy(dtype=float)

    s_none = weighted_slope(x, y, np.ones_like(v))
    s_lin = weighted_slope(x, y, v)
    s_sqrt = weighted_slope(x, y, np.sqrt(v))
    s_log = weighted_slope(x, y, np.log(v))

    print(f"{name:<20}{s_none:>+12.2f}{s_lin:>+12.2f}{s_sqrt:>+14.2f}{s_log:>+12.2f}")

print()
print("(value = rating change from start to end along the fitted trend; negative = decline)")
print()
print("Breaking Bad detail -- where its 5 most-voted episodes sit:")
sub = df[df["show_title"] == "Breaking Bad"]
show_id = sub.groupby("show_tconst")["num_votes"].sum().idxmax()
g = df[df["show_tconst"] == show_id].sort_values("overall_order")
n = len(g)
top5 = g.nlargest(5, "num_votes")
for _, r in top5.iterrows():
    pos = (r["overall_order"] - 1) / (n - 1)
    print(f"  overall_order={int(r['overall_order']):>3}/{n}  pos={pos:.2f}  votes={int(r['num_votes']):>8,}  rating={r['average_rating']}")
