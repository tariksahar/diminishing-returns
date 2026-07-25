"""Phase 1 output validation, checks 8-10: cross-check the titleType rule
against the raw basics file, verify value ranges are sane, and sanity-check
a few known shows. (Checks 1-7 -- row counts, schema, nulls, duplicates,
ongoing consistency, overall_order integrity, filter rules -- were run
inline when the build was first verified.)"""

import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")

print("=== 8. titleType RULE: cross-check against raw basics ===")
basics = pd.read_csv(
    "data/raw/title.basics.tsv.gz", sep="\t", na_values="\\N",
    usecols=["tconst", "titleType"], dtype=str,
)
show_types = basics.set_index("tconst")["titleType"]
df_types = df["show_tconst"].map(show_types)
bad_types = (~df_types.isin(["tvSeries", "tvMiniSeries"])).sum()
print(f"show_tconst values that are not tvSeries/tvMiniSeries: {bad_types}  -- should be 0")
print(f"types seen: {sorted(df_types.unique())}")
print()

print("=== 9. VALUE RANGES ===")
print(f"average_rating range: [{df['average_rating'].min()}, {df['average_rating'].max()}]  -- should sit within 0-10")
print(f"num_votes <= 0: {(df['num_votes'] <= 0).sum()}  -- should be 0")
print(f"season_number <= 0: {(df['season_number'] <= 0).sum()}")
print(f"episode_number <= 0: {(df['episode_number'] <= 0).sum()}")
bad_years = df[df["end_year"].notna() & (df["end_year"] < df["start_year"])]
print(f"rows with end_year < start_year: {len(bad_years)}  -- should be 0")
print()

print("=== 10. KNOWN-SHOW SANITY CHECK ===")
for name in ["Friends", "Game of Thrones", "The Sopranos"]:
    sub = df[df["show_title"] == name]
    if len(sub) == 0:
        print(f"{name}: NOT FOUND!")
        continue
    for show_id, g in sub.groupby("show_tconst"):
        print(
            f"{name} ({show_id}): {len(g)} episodes, {g['season_number'].nunique()} seasons, "
            f"ongoing={g['ongoing'].iloc[0]}, max overall_order={g['overall_order'].max()}"
        )
