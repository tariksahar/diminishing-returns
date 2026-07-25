"""Final tightening: how many 'found itself' shows have their RECOVERY on
statistically shaky (low-vote) ground?
  (a) descriptive: distribution of the last-third mean votes (the recovery
      region) among the found-itself shows.
  (b) robustness: drop episodes with < 100 votes, refit the quadratic, and
      see how many found-itself shows KEEP the label. If the recovery was
      only propped up by a low-vote tail, the label flips."""

import numpy as np
import pandas as pd

df = pd.read_parquet("data/processed/episodes.parquet")
shape = pd.read_json("data/processed/_phase2_shape_full.json")
fi_ids = shape[shape["shape"] == "found_itself"]["show_id"].tolist()

MIN_VOTES = 100


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


rows = []
for sid in fi_ids:
    g = df[df["show_tconst"] == sid].sort_values("overall_order")
    n = len(g)
    k = max(1, n // 3)
    last_third_votes = g.tail(k)["num_votes"].mean()

    # Refit after dropping thinly-voted episodes.
    gk = g[g["num_votes"] >= MIN_VOTES]
    if len(gk) >= 8 and gk["overall_order"].nunique() >= 3:
        nn = len(gk)
        x = (gk["overall_order"].to_numpy(float) - gk["overall_order"].min()) / \
            (gk["overall_order"].max() - gk["overall_order"].min())
        y = gk["average_rating"].to_numpy(float)
        new_label = quad_label(x, y, gk["num_votes"].to_numpy(float))
        dropped = n - nn
    else:
        new_label = "insufficient"
        dropped = n - len(gk)

    rows.append({"show_id": sid, "title": g["show_title"].iloc[0], "n_ep": n,
                 "last_third_votes": last_third_votes, "new_label": new_label,
                 "dropped": dropped})

r = pd.DataFrame(rows)

print("=" * 68)
print(f"(a) VOTES IN THE RECOVERY REGION (last third) -- {len(r)} found_itself shows")
print("=" * 68)
print(r["last_third_votes"].describe())
print()
for t in [50, 100, 200, 500]:
    c = (r["last_third_votes"] < t).sum()
    print(f"  last-third mean votes < {t:>4}: {c:>3} shows  ({100*c/len(r):.1f}%)")

print()
print("=" * 68)
print(f"(b) DOES THE LABEL SURVIVE DROPPING < {MIN_VOTES}-VOTE EPISODES?")
print("=" * 68)
print(r["new_label"].value_counts())
print()
kept = (r["new_label"] == "found_itself").sum()
usable = (r["new_label"] != "insufficient").sum()
print(f"shows with enough data left: {usable}/{len(r)}")
print(f"of those, still found_itself: {kept}  ({100*kept/usable:.1f}% of usable)")
flipped = r[(r["new_label"].isin(["jumped_the_shark", "linear/flat"]))]
print(f"label FLIPPED (recovery rested on low-vote episodes): {len(flipped)}")
print()
print("10 flipped shows with the thinnest recovery regions:")
for _, x in flipped.sort_values("last_third_votes").head(10).iterrows():
    print(f"  {x['title']:<32} last-third votes={x['last_third_votes']:>7,.0f}  "
          f"new={x['new_label']}  ({x['dropped']} episodes dropped)")
print()
print("Named-case check:")
for _, x in r[r["title"].isin(["Star Trek: Picard", "SpongeBob SquarePants", "Spy x Family"])].iterrows():
    print(f"  {x['title']:<24} last-third votes={x['last_third_votes']:>7,.0f}  new label={x['new_label']}")
