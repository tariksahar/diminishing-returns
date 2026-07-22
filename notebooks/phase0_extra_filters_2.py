"""Dig deeper into two filter questions: are the missing-endYear shows genuinely
ongoing (by inspecting their start years), and how do Documentary-tagged shows
split between anthology/magazine formats and season-based story documentaries."""

import pandas as pd

episodes = pd.read_csv("data/raw/title.episode.tsv.gz", sep="\t", na_values="\\N", dtype={"tconst": str, "parentTconst": str})
episodes["seasonNumber"] = pd.to_numeric(episodes["seasonNumber"], errors="coerce")
episodes["episodeNumber"] = pd.to_numeric(episodes["episodeNumber"], errors="coerce")
episodes = episodes.dropna(subset=["seasonNumber", "episodeNumber"])
ratings = pd.read_csv("data/raw/title.ratings.tsv.gz", sep="\t", na_values="\\N", dtype={"tconst": str})
ep = episodes.merge(ratings, on="tconst", how="inner")

basics = pd.read_csv(
    "data/raw/title.basics.tsv.gz",
    sep="\t",
    na_values="\\N",
    usecols=["tconst", "titleType", "primaryTitle", "startYear", "endYear", "genres"],
    dtype=str,
)
series = basics[basics["titleType"].isin(["tvSeries", "tvMiniSeries"])]
full = ep.merge(series.rename(columns={"tconst": "parentTconst"}), on="parentTconst", how="inner")

stats = full.groupby("parentTconst").agg(
    show_name=("primaryTitle", "first"),
    genres=("genres", "first"),
    start_year=("startYear", "first"),
    end_year=("endYear", "first"),
    episode_count=("tconst", "count"),
    mean_votes=("numVotes", "mean"),
    total_votes=("numVotes", "sum"),
).reset_index()

keep = stats[(stats["episode_count"] >= 13) & (stats["mean_votes"] >= 50)].copy()

# --- Question 1: are the 777 missing-endYear shows really ongoing, or just stale? ---
ongoing = keep[keep["end_year"].isna()].copy()
ongoing["start_year_num"] = pd.to_numeric(ongoing["start_year"], errors="coerce")

print("=== Missing-endYear shows: start-year distribution ===")
print(ongoing["start_year_num"].describe())
print()
print("Grouped by start year:")
print(f"  started 2023+: {(ongoing['start_year_num'] >= 2023).sum()}")
print(f"  started 2018-2022: {((ongoing['start_year_num'] >= 2018) & (ongoing['start_year_num'] < 2023)).sum()}")
print(f"  started 2010-2017: {((ongoing['start_year_num'] >= 2010) & (ongoing['start_year_num'] < 2018)).sum()}")
print(f"  started before 2010: {(ongoing['start_year_num'] < 2010).sum()}")
print()
print("Top 10 by total votes (recognizable? still airing?):")
top10 = ongoing.sort_values("total_votes", ascending=False).head(10)
for _, r in top10.iterrows():
    print(f"  {r['show_name']:<35} start:{r['start_year']}  episodes:{int(r['episode_count'])}")
print()
print("Started before 2010 but still no endYear (interesting/suspicious), top 10:")
old = ongoing[ongoing["start_year_num"] < 2010].sort_values("total_votes", ascending=False).head(10)
for _, r in old.iterrows():
    print(f"  {r['show_name']:<35} start:{r['start_year']}  episodes:{int(r['episode_count'])}")

print()
print("=" * 60)
print()

# --- Question 2: Documentary-tagged shows - how many, which ones ---
docs = keep[keep["genres"].str.contains("Documentary", na=False)].copy()
print(f"=== Documentary-tagged shows (passing threshold): {len(docs)} ===")
docs_sorted = docs.sort_values("total_votes", ascending=False)
for _, r in docs_sorted.iterrows():
    print(f"  {r['show_name']:<40} genres:{r['genres']:<40} episodes:{int(r['episode_count']):>4}  total_votes:{int(r['total_votes']):>8}")
