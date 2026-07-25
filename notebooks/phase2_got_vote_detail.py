"""Where do Game of Thrones' most-voted episodes sit in its run? This is the
concrete case behind rejecting raw-vote weighting: its two highest-vote
episodes are its last two, so linear weighting lets the finale backlash
dominate the fitted trend."""

import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")
sub = df[df["show_title"] == "Game of Thrones"]
show_id = sub.groupby("show_tconst")["num_votes"].sum().idxmax()
g = df[df["show_tconst"] == show_id].sort_values("overall_order")
n = len(g)
top5 = g.nlargest(5, "num_votes")
print("Game of Thrones -- 5 most-voted episodes:")
for _, r in top5.iterrows():
    pos = (r["overall_order"] - 1) / (n - 1)
    print(f"  overall_order={int(r['overall_order']):>3}/{n}  pos={pos:.2f}  "
          f"votes={int(r['num_votes']):>8,}  rating={r['average_rating']}")
