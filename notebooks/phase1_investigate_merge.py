"""Phase 1 merge safety checks: confirm tconst is unique in each raw file
(so the joins cannot silently multiply rows), and confirm the genres field
has no hidden whitespace or spelling variants that would make the
Documentary rule miss shows."""

import pandas as pd

print("=== Is tconst unique in the raw files? (row-multiplication risk) ===")
ratings = pd.read_csv("data/raw/title.ratings.tsv.gz", sep="\t", na_values="\\N", dtype={"tconst": str})
print(f"title.ratings: {len(ratings):,} rows, {ratings['tconst'].nunique():,} unique tconst -- should match")

basics_ids = pd.read_csv("data/raw/title.basics.tsv.gz", sep="\t", na_values="\\N",
                         usecols=["tconst"], dtype=str)
print(f"title.basics: {len(basics_ids):,} rows, {basics_ids['tconst'].nunique():,} unique tconst -- should match")

episodes = pd.read_csv("data/raw/title.episode.tsv.gz", sep="\t", na_values="\\N",
                       dtype={"tconst": str, "parentTconst": str})
print(f"title.episode: {len(episodes):,} rows, {episodes['tconst'].nunique():,} unique tconst "
      "-- should match (one row per episode)")
print()

print("=== Any whitespace or hidden variants in the genres field? ===")
genres_col = pd.read_csv("data/raw/title.basics.tsv.gz", sep="\t", na_values="\\N",
                         usecols=["genres"], dtype=str)["genres"].dropna().unique()
all_genre_tokens = set()
for g in genres_col:
    for tok in g.split(","):
        all_genre_tokens.add(tok)
suspicious = [t for t in all_genre_tokens if t != t.strip()]
print(f"total unique genre tokens: {len(all_genre_tokens)}")
print(f"suspicious (untrimmed) tokens: {suspicious}")
print("exact 'Documentary' match present:", "Documentary" in all_genre_tokens)
doc_variants = [t for t in all_genre_tokens if "ocument" in t]
print(f"all tokens containing 'ocument': {doc_variants}")
