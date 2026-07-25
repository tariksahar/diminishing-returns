"""Is the 'newer shows rise' era effect real, or a confound with show length
and ongoing status? Check the composition of each decade, then re-run the
decade cut on ENDED shows only, and within a fixed length band."""

import pandas as pd

s = pd.read_json("data/processed/_phase2_slopes_full.json")
s["start_year"] = pd.to_numeric(s["start_year"], errors="coerce")
s = s[s["start_year"].notna()].copy()
s["decade"] = (s["start_year"] // 10 * 10).astype(int)

print("=" * 74)
print("DECADE COMPOSITION (why a standalone era effect is suspect)")
print("=" * 74)
print(f"{'decade':<8}{'n':>6}{'ongoing%':>10}{'med seasons':>14}{'med episodes':>14}{'med mean rating':>18}")
for dec, g in s.groupby("decade"):
    if len(g) < 15:
        continue
    print(f"{dec:<8}{len(g):>6}{100*g['ongoing'].mean():>9.0f}%{g['n_season'].median():>14.0f}"
          f"{g['n_ep'].median():>14.0f}{g['mean_rating'].median():>18.2f}")

print()
print("=" * 74)
print("TEST: DOES THE ERA EFFECT HOLD AMONG ENDED SHOWS ONLY?")
print("=" * 74)
ended = s[~s["ongoing"]]
print(f"{'decade':<8}{'n':>6}{'median slope':>15}{'declining%':>13}")
for dec, g in ended.groupby("decade"):
    if len(g) < 15:
        continue
    print(f"{dec:<8}{len(g):>6}{g['slope'].median():>15.3f}{100*(g['slope']<0).mean():>12.0f}%")

print()
print("=" * 74)
print("TEST: ERA EFFECT WITH LENGTH HELD FIXED (ended, 2-3 season shows only)")
print("=" * 74)
band = ended[ended["n_season"].isin([2, 3])]
print(f"{'decade':<8}{'n':>6}{'median slope':>15}{'declining%':>13}")
for dec, g in band.groupby("decade"):
    if len(g) < 15:
        continue
    print(f"{dec:<8}{len(g):>6}{g['slope'].median():>15.3f}{100*(g['slope']<0).mean():>12.0f}%")

print()
print("=" * 74)
print("LENGTH VS ERA: which separates shows more strongly?")
print("(if the era effect faded among ended 2-3 season shows, era would be")
print(" largely a length/ongoing confound -- it does not fade)")
print("=" * 74)
print(f"median slope, ended 2-3 season shows: {band['slope'].median():+.3f}")
print(f"median slope, ended 6+ season shows:  {ended[ended['n_season']>=6]['slope'].median():+.3f}")
