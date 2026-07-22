"""Apply the combined draft thresholds (>=13 episodes AND mean votes/episode >=50)
and verify the three example shows survive them."""

import pandas as pd

episodes = pd.read_csv("data/raw/title.episode.tsv.gz", sep="\t", na_values="\\N", dtype={"tconst": str, "parentTconst": str})
episodes["seasonNumber"] = pd.to_numeric(episodes["seasonNumber"], errors="coerce")
episodes["episodeNumber"] = pd.to_numeric(episodes["episodeNumber"], errors="coerce")
episodes = episodes.dropna(subset=["seasonNumber", "episodeNumber"])
ratings = pd.read_csv("data/raw/title.ratings.tsv.gz", sep="\t", na_values="\\N", dtype={"tconst": str})
ep = episodes.merge(ratings, on="tconst", how="inner")
basics = pd.read_csv("data/raw/title.basics.tsv.gz", sep="\t", na_values="\\N", usecols=["tconst", "titleType", "primaryTitle", "startYear", "genres"], dtype=str)
series = basics[basics["titleType"].isin(["tvSeries", "tvMiniSeries"])]
full = ep.merge(series.rename(columns={"tconst": "parentTconst"}), on="parentTconst", how="inner")

stats = full.groupby("parentTconst").agg(
    show_name=("primaryTitle", "first"),
    episode_count=("tconst", "count"),
    mean_votes=("numVotes", "mean"),
).reset_index()

keep = stats[(stats["episode_count"] >= 13) & (stats["mean_votes"] >= 50)]
print("THRESHOLD: >=13 episodes AND mean votes/episode >=50")
print(f"Shows remaining: {len(keep):,}  ({100 * len(keep) / len(stats):.1f}% of all shows)")
kept_episodes = full[full["parentTconst"].isin(keep["parentTconst"])]
print(f"Total episodes remaining: {len(kept_episodes):,}")
print()
print("Do our example shows pass the thresholds:")
for name in ["Friends", "Game of Thrones", "The Sopranos"]:
    rows = stats[stats["show_name"] == name].sort_values("episode_count", ascending=False).head(1)
    for _, r in rows.iterrows():
        ok = "PASS" if (r["episode_count"] >= 13 and r["mean_votes"] >= 50) else "DROPPED"
        print(f"  {name}: {int(r['episode_count'])} episodes, mean {r['mean_votes']:.0f} votes/episode -> {ok}")
