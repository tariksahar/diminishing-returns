import pandas as pd
import matplotlib.pyplot as plt

RAW = "data/raw"

# 1. Bolum -> dizi eslestirme tablosu: her bolumun hangi diziye (parentTconst)
#    ve o dizinin kacinci sezon/bolumune ait oldugunu tasiyor.
episodes = pd.read_csv(
    f"{RAW}/title.episode.tsv.gz",
    sep="\t",
    na_values="\\N",
    dtype={"tconst": str, "parentTconst": str},
)
episodes["seasonNumber"] = pd.to_numeric(episodes["seasonNumber"], errors="coerce")
episodes["episodeNumber"] = pd.to_numeric(episodes["episodeNumber"], errors="coerce")
episodes_clean = episodes.dropna(subset=["seasonNumber", "episodeNumber"])
print(f"title.episode toplam satir: {len(episodes):,}")
print(f"sezon/bolum no'su eksiksiz olan satir: {len(episodes_clean):,}")

# 2. Puanlar: her title (bolum dahil) icin ortalama puan ve oy sayisi.
ratings = pd.read_csv(
    f"{RAW}/title.ratings.tsv.gz",
    sep="\t",
    na_values="\\N",
    dtype={"tconst": str},
)

# 3. Bolum + puan join (inner): sadece en az 1 oy almis bolumler hayatta kalir.
ep_ratings = episodes_clean.merge(ratings, on="tconst", how="inner")
print(f"puani olan bolum sayisi (join sonrasi): {len(ep_ratings):,}")

# 4. Dizi kimlik bilgisi: title.basics'ten sadece tvSeries / tvMiniSeries.
basics = pd.read_csv(
    f"{RAW}/title.basics.tsv.gz",
    sep="\t",
    na_values="\\N",
    usecols=["tconst", "titleType", "primaryTitle", "startYear", "genres"],
    dtype=str,
)
series = basics[basics["titleType"].isin(["tvSeries", "tvMiniSeries"])].copy()
print(f"toplam tvSeries/tvMiniSeries sayisi: {len(series):,}")

# 5. Bolum+puan tablosunu dizi bilgisiyle birlestir (parentTconst = dizinin tconst'u).
full = ep_ratings.merge(
    series.rename(columns={"tconst": "parentTconst"}),
    on="parentTconst",
    how="inner",
)
print(f"nihai (puanli + dizi bilgili) bolum sayisi: {len(full):,}")

# 6. Genel sira: dizinin kendi icinde sezon/bolum sirasina gore 1'den basayan bolum indeksi.
full = full.sort_values(["parentTconst", "seasonNumber", "episodeNumber"])
full["genel_sira"] = full.groupby("parentTconst").cumcount() + 1

# 7. Ornek 3 diziyi bul ve ciz.
examples = [("Friends", "1994"), ("Game of Thrones", "2011"), ("The Sopranos", "1999")]

fig, axes = plt.subplots(len(examples), 1, figsize=(9, 10), sharex=False)

for ax, (name, year) in zip(axes, examples):
    subset = full[(full["primaryTitle"] == name) & (full["startYear"] == year)]
    subset = subset.sort_values("genel_sira")
    print(f"{name} ({year}) -> bulunan bolum sayisi: {len(subset)}")
    ax.plot(subset["genel_sira"], subset["averageRating"], marker="o", markersize=2, linewidth=0.8)
    ax.set_title(f"{name} ({year}) - bolum bolum puan")
    ax.set_xlabel("Genel bolum sirasi")
    ax.set_ylabel("Puan (averageRating)")
    ax.set_ylim(0, 10)
    ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("figures/faz0_ornek_egriler.png", dpi=150)
print("Grafik kaydedildi: figures/faz0_ornek_egriler.png")

# 8. Dizi bazinda dagilim: kac bolumu var, bolum basina ortalama kac oy aldi.
show_stats = full.groupby("parentTconst").agg(
    dizi_adi=("primaryTitle", "first"),
    tur=("genres", "first"),
    baslangic_yili=("startYear", "first"),
    bolum_sayisi=("tconst", "count"),
    toplam_oy=("numVotes", "sum"),
    ortalama_oy_sayisi=("numVotes", "mean"),
    medyan_oy_sayisi=("numVotes", "median"),
).reset_index()

print()
print(f"En az 1 puanli bolumu olan farkli dizi sayisi: {len(show_stats):,}")
print()
print("Bolum sayisi dagilimi:")
print(show_stats["bolum_sayisi"].describe())
print()
for n in [1, 2, 3, 5, 8, 10, 13, 20, 30]:
    count = (show_stats["bolum_sayisi"] >= n).sum()
    pct = 100 * count / len(show_stats)
    print(f"  >= {n} bolum: {count:,} dizi (%{pct:.1f})")

print()
print("Bolum basina ortalama oy sayisi dagilimi:")
print(show_stats["ortalama_oy_sayisi"].describe())
print()
for v in [10, 25, 50, 100, 500, 1000]:
    count = (show_stats["ortalama_oy_sayisi"] >= v).sum()
    pct = 100 * count / len(show_stats)
    print(f"  bolum basina ort. oy >= {v}: {count:,} dizi (%{pct:.1f})")

# Iki kosulu birlikte uygulayinca ne kadar dizi kaliyor (kaba bir taslak icin).
combo = show_stats[(show_stats["bolum_sayisi"] >= 8) & (show_stats["ortalama_oy_sayisi"] >= 100)]
print()
print(f"Taslak: >=8 bolum VE bolum basina ort. oy >=100 -> {len(combo):,} dizi")

fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
ax1.hist(show_stats["bolum_sayisi"].clip(upper=100), bins=50)
ax1.set_xlabel("Bolum sayisi (100'de kirpildi)")
ax1.set_ylabel("Dizi sayisi")
ax1.set_title("Dizi basina bolum sayisi dagilimi")

ax2.hist(show_stats["ortalama_oy_sayisi"].clip(upper=2000), bins=50)
ax2.set_xlabel("Bolum basina ort. oy sayisi (2000'de kirpildi)")
ax2.set_ylabel("Dizi sayisi")
ax2.set_title("Dizi basina ortalama oy sayisi dagilimi")

plt.tight_layout()
plt.savefig("figures/faz0_esik_dagilimi.png", dpi=150)
print("Grafik kaydedildi: figures/faz0_esik_dagilimi.png")
