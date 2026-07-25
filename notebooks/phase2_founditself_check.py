"""Is the 'found itself' (U-shaped, dip-then-recover) label a real pattern or
an artifact of early episodes having fewer votes (hence noisier / possibly
biased-low ratings)? Five independent checks."""

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")
shape = pd.read_json("data/processed/_phase2_shape_full.json")  # sqrt-weighted labels


def quad_label(x, y, w):
    X = np.column_stack([np.ones_like(x), x, x**2])
    sw = np.sqrt(w)
    coef, *_ = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)
    a, b, c = coef
    vertex = -b / (2 * c) if abs(c) > 1e-6 else None
    lab = "linear/flat"
    if vertex is not None and 0.15 <= vertex <= 0.85:
        if c < -0.05:
            lab = "jumped_the_shark"
        elif c > 0.05:
            lab = "found_itself"
    return lab


# Recompute labels without weighting, for a robustness comparison.
unw = {}
pos_vote_corr = []
for show_id, g in df.groupby("show_tconst"):
    g = g.sort_values("overall_order")
    n = len(g)
    x = (g["overall_order"].to_numpy(float) - 1) / (n - 1)
    y = g["average_rating"].to_numpy(float)
    unw[show_id] = quad_label(x, y, np.ones(n))
    # Within-show position vs votes: do late episodes get more or fewer votes?
    v = g["num_votes"].to_numpy(float)
    if n >= 5 and np.std(v) > 0:
        pos_vote_corr.append(np.corrcoef(x, np.log1p(v))[0, 1])

shape["unw_shape"] = shape["show_id"].map(unw)

print("=" * 68)
print("TEST 1: ROBUSTNESS TO WEIGHTING (sqrt vs unweighted)")
print("=" * 68)
ct = pd.crosstab(shape["shape"], shape["unw_shape"])
print(ct)
fi = shape[shape["shape"] == "found_itself"]
stay = (fi["unw_shape"] == "found_itself").mean()
print()
print(f"Of the {len(fi)} shows labelled 'found_itself' under sqrt weighting,")
print(f"{100*stay:.1f}% keep that label unweighted.")
print("(A low share would mean the label is a product of the weighting = suspect.)")

print()
print("=" * 68)
print("TEST 2: IS IT CONCENTRATED IN SHORT SHOWS? (overfitting risk)")
print("=" * 68)
for lab in ["jumped_the_shark", "linear/flat", "found_itself"]:
    sub = shape[shape["shape"] == lab]
    print(f"  {lab:<17} n={len(sub):<5} median episodes={sub['n_ep'].median():>5.0f}  "
          f"median seasons={sub['n_season'].median():>3.0f}")

print()
print("=" * 68)
print("TEST 3: DOES THE 'DIP' COINCIDE WITH LOW-VOTE EPISODES?")
print("(found_itself shows: first third vs last third, ratings and votes)")
print("=" * 68)
first_r, last_r, first_v, last_v = [], [], [], []
for show_id in fi["show_id"]:
    g = df[df["show_tconst"] == show_id].sort_values("overall_order")
    n = len(g)
    k = max(1, n // 3)
    fr = g.head(k)
    lr = g.tail(k)
    first_r.append(fr["average_rating"].mean()); last_r.append(lr["average_rating"].mean())
    first_v.append(fr["num_votes"].mean());       last_v.append(lr["num_votes"].mean())
first_r, last_r = np.array(first_r), np.array(last_r)
first_v, last_v = np.array(first_v), np.array(last_v)
print(f"  mean RATING  first third: {first_r.mean():.2f}   last third: {last_r.mean():.2f}   "
      f"difference: {last_r.mean()-first_r.mean():+.2f}")
print(f"  mean VOTES   first third: {first_v.mean():,.0f}   last third: {last_v.mean():,.0f}")
print(f"  share of found_itself shows whose first third has FEWER votes: "
      f"{100*(first_v < last_v).mean():.1f}%")
print("  -> if early episodes were both low-rated and thinly voted, the 'dip'")
print("     would rest on weak statistical ground")

print()
print("=" * 68)
print("TEST 4: VOTES vs POSITION, AND VOTES vs RATING")
print("=" * 68)
pvc = np.array(pos_vote_corr)
print(f"mean within-show correlation of position with log(votes): {pvc.mean():+.3f}")
print("  (positive would mean late episodes attract more votes, i.e. early ones are thin)")
print(f"  share of shows where early episodes are the thinly-voted ones: {100*(pvc>0).mean():.1f}%")
print()
# Global relationship between vote volume and rating.
df2 = df.copy()
df2["vote_decile"] = pd.qcut(df2["num_votes"], 10, labels=False, duplicates="drop")
dec = df2.groupby("vote_decile")["average_rating"].mean()
print("Mean rating by vote decile (0 = fewest votes, 9 = most):")
for d, r in dec.items():
    print(f"  decile {int(d)}: {r:.2f}")
print("  -> a monotone rise means low-vote episodes are systematically rated lower")

print()
print("=" * 68)
print("TEST 5: NAMED CASES (per-season rating and votes)")
print("=" * 68)
for title in ["Star Trek: Picard", "SpongeBob SquarePants", "Spy x Family"]:
    sub = df[df["show_title"] == title]
    if sub.empty:
        continue
    sid = sub.groupby("show_tconst")["num_votes"].sum().idxmax()
    g = df[df["show_tconst"] == sid]
    sm = g.groupby("season_number").agg(mean_rating=("average_rating", "mean"),
                                        mean_votes=("num_votes", "mean"),
                                        n=("average_rating", "size"))
    print(f"\n{title}:")
    for s, row in sm.iterrows():
        print(f"  S{int(s):<2} rating={row['mean_rating']:.2f}  mean votes={row['mean_votes']:>8,.0f}  "
              f"({int(row['n'])} episodes)")
