"""How much do vote counts vary BETWEEN episodes of the same show? If they
vary a lot, weighting matters; if every episode has similar votes, it barely
moves the trend line. Quantify within-show vote spread and show examples."""

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")

ratios = []
for show_id, g in df.groupby("show_tconst"):
    v = g["num_votes"].to_numpy()
    ratios.append(v.max() / v.min())
ratios = np.array(ratios)

print("=== Within-show vote spread: max-votes / min-votes per show ===")
print(f"median ratio: {np.median(ratios):.1f}x")
print(f"mean ratio:   {np.mean(ratios):.1f}x")
print(f"75th pct:     {np.percentile(ratios, 75):.1f}x")
print(f"90th pct:     {np.percentile(ratios, 90):.1f}x")
print(f"shows where busiest episode has >10x the votes of quietest: "
      f"{(ratios > 10).sum():,} ({100*(ratios>10).mean():.0f}%)")
print()

print("=== Concrete examples: least vs most voted episode ===")
for name in ["Friends", "Game of Thrones", "Breaking Bad"]:
    sub = df[df["show_title"] == name]
    if len(sub) == 0:
        continue
    # pick the highest-vote version if duplicated titles
    show_id = sub.groupby("show_tconst")["num_votes"].sum().idxmax()
    g = sub[sub["show_tconst"] == show_id]
    lo = g.loc[g["num_votes"].idxmin()]
    hi = g.loc[g["num_votes"].idxmax()]
    print(f"{name}:")
    print(f"   quietest ep: S{int(lo['season_number'])}E{int(lo['episode_number'])}  "
          f"{int(lo['num_votes']):>7,} votes  rating {lo['average_rating']}")
    print(f"   busiest  ep: S{int(hi['season_number'])}E{int(hi['episode_number'])}  "
          f"{int(hi['num_votes']):>7,} votes  rating {hi['average_rating']}")
