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
    dizi_adi=("primaryTitle", "first"),
    bolum_sayisi=("tconst", "count"),
    ort_oy=("numVotes", "mean"),
).reset_index()

keep = stats[(stats["bolum_sayisi"] >= 13) & (stats["ort_oy"] >= 50)]
print("ESIK: >=13 bolum VE bolum basina ort. oy >=50")
print(f"Kalan dizi sayisi: {len(keep):,}  (tum dizilerin %{100*len(keep)/len(stats):.1f}u)")
kept_episodes = full[full["parentTconst"].isin(keep["parentTconst"])]
print(f"Kalan toplam bolum sayisi: {len(kept_episodes):,}")
print()
print("Ornek dizilerimiz esikleri geciyor mu:")
for name in ["Friends", "Game of Thrones", "The Sopranos"]:
    rows = stats[stats["dizi_adi"] == name].sort_values("bolum_sayisi", ascending=False).head(1)
    for _, r in rows.iterrows():
        ok = "GECER" if (r["bolum_sayisi"] >= 13 and r["ort_oy"] >= 50) else "ELENIR"
        print(f"  {name}: {int(r['bolum_sayisi'])} bolum, bolum basina ort. {r['ort_oy']:.0f} oy -> {ok}")
