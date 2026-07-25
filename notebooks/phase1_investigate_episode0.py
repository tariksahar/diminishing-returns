"""Phase 1 follow-up: the build output contains rows with episode_number <= 0,
which looked like a bug. Inspect them to decide whether they are corrupt or
genuine IMDb data (they turned out to be real: IMDb numbers some specials and
pilots as episode 0)."""

import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")

bad = df[df["episode_number"] <= 0]
print(f"rows with episode_number <= 0: {len(bad)}")
print()
print("episode_number value counts:")
print(bad["episode_number"].value_counts())
print()
print("season_number distribution among those rows:")
print(bad["season_number"].value_counts().head(10))
print()
print("10 example rows:")
print(bad[["show_title", "season_number", "episode_number", "overall_order", "average_rating"]].head(10).to_string())
print()
# What do these episode-0 rows sit next to within their own show?
show_id = bad.iloc[0]["show_tconst"]
print(f"Example show ({bad.iloc[0]['show_title']}) -- first 8 episodes in order:")
one_show = df[df["show_tconst"] == show_id].sort_values("overall_order")
print(one_show[["season_number", "episode_number", "overall_order", "average_rating"]].head(8).to_string())
