"""Game of Thrones season 8: compare the season's TRUE mean rating against
what the fitted trend line predicts in that stretch, under each weighting
scheme. This is the case that showed the overall slope cannot stand in for
the final-season question -- a straight line stays anchored to the 67
consistently-high episodes and understates the late crash."""

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")
sub = df[df["show_title"] == "Game of Thrones"]
show_id = sub.groupby("show_tconst")["num_votes"].sum().idxmax()
g = df[df["show_tconst"] == show_id].sort_values("overall_order")
n = len(g)

s8 = g[g["season_number"] == 8]
rest = g[g["season_number"] != 8]

print(f"Season 8 true mean rating: {s8['average_rating'].mean():.2f}  ({len(s8)} episodes)")
print("Season 8 episodes:", list(zip(s8["episode_number"], s8["average_rating"])))
print(f"Seasons 1-7 true mean rating: {rest['average_rating'].mean():.2f}  ({len(rest)} episodes)")
print()

x = (g["overall_order"].to_numpy(dtype=float) - 1) / (n - 1)
y = g["average_rating"].to_numpy(dtype=float)
v = g["num_votes"].to_numpy(dtype=float)


def weighted_fit(x, y, w):
    W = np.sum(w)
    x_bar = np.sum(w * x) / W
    y_bar = np.sum(w * y) / W
    b = np.sum(w * (x - x_bar) * (y - y_bar)) / np.sum(w * (x - x_bar) ** 2)
    a = y_bar - b * x_bar
    return a, b


x_min_norm = (s8["overall_order"].min() - 1) / (n - 1)
x_max_norm = (s8["overall_order"].max() - 1) / (n - 1)
print(f"Season 8 normalized x range: {x_min_norm:.3f} - {x_max_norm:.3f}")
print()

for label, w in [("unweighted", np.ones_like(v)), ("sqrt(votes)", np.sqrt(v)), ("votes (linear)", v)]:
    a, b = weighted_fit(x, y, w)
    pred_start = a + b * x_min_norm
    pred_end = a + b * x_max_norm
    print(f"{label:<16}: trend line across the season-8 range = {pred_start:.2f} -> {pred_end:.2f}")

print()
print("All schemes predict well above the true 6.40, which is why the")
print("final-season analysis uses a direct season-mean comparison instead.")
