"""Test the >=2 seasons filter (Sherlock should survive, single-season anime
giants should drop) and illustrate per-episode vote noise using Friends."""

import pandas as pd

episodes = pd.read_csv("data/raw/title.episode.tsv.gz", sep="\t", na_values="\\N", dtype={"tconst": str, "parentTconst": str})
episodes["seasonNumber"] = pd.to_numeric(episodes["seasonNumber"], errors="coerce")
episodes["episodeNumber"] = pd.to_numeric(episodes["episodeNumber"], errors="coerce")
episodes = episodes.dropna(subset=["seasonNumber", "episodeNumber"])
ratings = pd.read_csv("data/raw/title.ratings.tsv.gz", sep="\t", na_values="\\N", dtype={"tconst": str})
ep = episodes.merge(ratings, on="tconst", how="inner")

basics = pd.read_csv(
    "data/raw/title.basics.tsv.gz", sep="\t", na_values="\\N",
    usecols=["tconst", "titleType", "primaryTitle", "startYear", "endYear", "genres"], dtype=str,
)
series = basics[basics["titleType"].isin(["tvSeries", "tvMiniSeries"])]
full = ep.merge(series.rename(columns={"tconst": "parentTconst"}), on="parentTconst", how="inner")

stats = full.groupby("parentTconst").agg(
    show_name=("primaryTitle", "first"),
    start_year=("startYear", "first"),
    episode_count=("tconst", "count"),
    season_count=("seasonNumber", "nunique"),
    mean_votes=("numVotes", "mean"),
).reset_index()

print("=== Sherlock check ===")
sherlock = stats[stats["show_name"] == "Sherlock"]
print(sherlock[["show_name", "start_year", "episode_count", "season_count", "mean_votes"]])
print()

print("=== Old threshold (>=13 ep, mean votes>=50) vs new (+ season_count>=2) ===")
old = stats[(stats["episode_count"] >= 13) & (stats["mean_votes"] >= 50)]
new = stats[(stats["episode_count"] >= 13) & (stats["mean_votes"] >= 50) & (stats["season_count"] >= 2)]
print(f"Shows under old threshold: {len(old):,}")
print(f"Shows after adding season condition: {len(new):,}")
print(f"Shows dropped by season condition: {len(old) - len(new):,}")
print()
print("Examples dropped by the season condition (single-season but >=13 episodes), top 10:")
dropped = old[~old["parentTconst"].isin(new["parentTconst"])].sort_values("episode_count", ascending=False)
for _, r in dropped.head(10).iterrows():
    print(f"  {r['show_name']:<35} episodes:{int(r['episode_count']):>4}  seasons:{int(r['season_count'])}")

print()
print("=" * 60)
print()

print("=== Per-episode vote noise - Friends example ===")
friends = full[(full["primaryTitle"] == "Friends") & (full["startYear"] == "1994")].copy()
friends = friends.sort_values(["seasonNumber", "episodeNumber"])
friends["overall_order"] = range(1, len(friends) + 1)
print(f"Total episodes: {len(friends)}")
print("5 least-voted episodes:")
print(friends.sort_values("numVotes").head(5)[["overall_order", "seasonNumber", "episodeNumber", "numVotes", "averageRating"]].to_string(index=False))
print()
print("5 most-voted episodes:")
print(friends.sort_values("numVotes", ascending=False).head(5)[["overall_order", "seasonNumber", "episodeNumber", "numVotes", "averageRating"]].to_string(index=False))
print()
print("Vote-count stats (per episode):")
print(friends["numVotes"].describe())
