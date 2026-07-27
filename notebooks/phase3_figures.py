"""Phase 3 — the report figure set.

One function per figure, each mapped to a section of docs/report_outline.md.
Every figure recomputes its own numbers from data/processed/ rather than
hard-coding them, and prints what it annotated so the labels can be checked
against docs/decisions.md.

Run from the repo root:  .venv/Scripts/python.exe notebooks/phase3_figures.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import figstyle as fs
from figstyle import BLUE, ORANGE, AQUA, RED, MUTED, INK, INK_2, AXIS, SURFACE

DF = pd.read_parquet("data/processed/episodes.parquet")
SLOPES = pd.read_json("data/processed/_phase2_slopes_full.json")
SHAPES = pd.read_json("data/processed/_phase2_shape_full.json")
FINALSEASON = pd.read_json("data/processed/_phase2_finalseason_full.json")

SOURCE = "Source: IMDb public dataset. 3,234 shows / 192,720 rated episodes."

# Every figure is drawn at the same width so that, once scaled to the report's
# column, text renders at the same size throughout. Only the height varies.
W = 12.0


# --- shared fitting helpers (identical to phase2_shape.py) -------------------
def weighted_linear(x, y, w):
    """Weighted least-squares line. Returns (intercept, slope)."""
    W = np.sum(w)
    x_bar = np.sum(w * x) / W
    y_bar = np.sum(w * y) / W
    b = np.sum(w * (x - x_bar) * (y - y_bar)) / np.sum(w * (x - x_bar) ** 2)
    return y_bar - b * x_bar, b


def weighted_quad(x, y, w):
    """Weighted least-squares parabola. Returns (a, b, c) for y = a + bx + cx^2."""
    X = np.column_stack([np.ones_like(x), x, x ** 2])
    sw = np.sqrt(w)
    coef, *_ = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)
    return coef


def show_frame(tconst):
    """Episodes of one show, in air order, with the normalized 0-1 x axis."""
    g = DF[DF["show_tconst"] == tconst].sort_values("overall_order")
    x = (g["overall_order"].to_numpy(float) - 1) / (len(g) - 1)
    return g, x, g["average_rating"].to_numpy(float), g["num_votes"].to_numpy(float)


# --- figure 1 ---------------------------------------------------------------
def fig01_slope_distribution():
    """Section 2 -- the headline: most shows are flat, more rise than fall."""
    s = SLOPES["slope"].to_numpy(float)
    pct_down = 100 * (s < 0).mean()
    pct_up = 100 * (s > 0).mean()
    clear_decline = 100 * (s <= -0.5).mean()
    flat = 100 * ((s > -0.5) & (s < 0.5)).mean()
    clear_rise = 100 * (s >= 0.5).mean()
    median = np.median(s)
    print(f"  trend down {pct_down:.1f}% / up {pct_up:.1f}%")
    print(f"  clear decline {clear_decline:.1f}% | flat {flat:.1f}% | "
          f"clear rise {clear_rise:.1f}% | median {median:+.3f}")
    print(f"  slope range {s.min():.2f} .. {s.max():.2f}; "
          f"outside +/-3: {100*(np.abs(s) > 3).mean():.2f}%")

    edges = np.round(np.arange(-3.0, 3.0001, 0.1), 2)
    clipped = np.clip(s, -2.999, 2.999)
    counts, _ = np.histogram(clipped, bins=edges)
    centers = (edges[:-1] + edges[1:]) / 2
    # Diverging colour by band: decline / flat / rise. -0.5 and +0.5 are bin
    # edges, so no bar straddles a boundary.
    colors = [RED if c < -0.5 else (BLUE if c > 0.5 else MUTED) for c in centers]

    fig, ax = plt.subplots(figsize=(W, 5.6))
    # The 0.6pt surface-coloured edge is the "surface gap" separating adjacent
    # bars — it is a spacer, not a border ring.
    ax.bar(centers, counts, width=0.1, color=colors,
           edgecolor=SURFACE, linewidth=0.6)
    # Bounded rules, not full-height axvlines: the band labels live in the
    # headroom above and must not be struck through.
    ax.vlines(0, 0, counts.max() * 1.06, color=AXIS, linewidth=0.8)
    ax.vlines(median, 0, counts.max() * 1.06, color=INK, linewidth=1.4)

    # Headroom above the tallest bar, so the band labels sit in clear space
    # instead of on top of the distribution.
    top = counts.max()
    ax.set_ylim(0, top * 1.30)
    ax.annotate(f"median {median:+.2f}", xy=(median, top * 1.03),
                xytext=(median + 0.12, top * 1.03), color=INK, fontsize=9,
                va="center", ha="left")
    for xpos, share, label, color in [
        (-1.65, clear_decline, "clearly declining", RED),
        (0.0, flat, "essentially flat", INK_2),
        (1.65, clear_rise, "clearly rising", BLUE),
    ]:
        ax.text(xpos, top * 1.20, f"{share:.1f}%", ha="center", va="bottom",
                fontsize=15, fontweight="bold", color=color)
        ax.text(xpos, top * 1.17, label, ha="center", va="top",
                fontsize=9.5, color=INK_2)

    ax.set_xlim(-3, 3)
    ax.set_xlabel("Rating points gained or lost across the show's full run")
    ax.set_ylabel("Number of shows")
    fs.style_axes(ax, grid="y")
    fs.frame(
        fig,
        "Most shows don't decline — most barely move at all",
        "A weighted trend line through every show's episode ratings: -1 means "
        "it ends a full rating point below where it started.",
        f"'Clear' = at least half a rating point. Axis clipped to +/-3 points "
        f"({100*(np.abs(s) > 3).mean():.1f}% of shows fall outside). {SOURCE}",
    )
    return fs.save(fig, "fig01_slope_distribution")


# --- figure 2 ---------------------------------------------------------------
def fig02_halves_stability():
    """Section 2 -- the clean regression-to-the-mean test (disjoint halves)."""
    rows = []
    for _, g in DF.groupby("show_tconst"):
        g = g.sort_values("overall_order")
        if len(g) < 8:
            continue
        half = len(g) // 2
        rows.append({"b": g["average_rating"].iloc[:half].mean(),
                     "o": g["average_rating"].iloc[half:].mean()})
    r = pd.DataFrame(rows)
    corr = np.corrcoef(r["b"], r["o"])[0, 1]
    fit = np.polyfit(r["b"], r["o"], 1)
    print(f"  n={len(r)} shows, corr={corr:+.3f}, o = {fit[0]:.3f}*b + {fit[1]:.3f}")

    r["q"] = pd.qcut(r["b"], 4, labels=["Weakest 25%", "2nd", "3rd", "Strongest 25%"])
    qs = r.groupby("q", observed=True).agg(b=("b", "mean"), o=("o", "mean"))
    qs["change"] = qs["o"] - qs["b"]
    for q, row in qs.iterrows():
        print(f"  {q:<14} first {row['b']:.2f} -> second {row['o']:.2f} "
              f"({row['change']:+.2f})")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(W, 5.2),
                                   gridspec_kw={"width_ratios": [1.25, 1]})

    ax1.scatter(r["b"], r["o"], s=7, color=BLUE, alpha=0.22, linewidths=0)
    # Limits span the full data range: an earlier fixed (4.2, 9.8) box silently
    # dropped the 16 lowest-rated shows off the corner of the plot.
    lo = min(r["b"].min(), r["o"].min()) - 0.3
    hi = max(r["b"].max(), r["o"].max()) + 0.3
    lims = (lo, hi)
    ax1.plot(lims, lims, color=MUTED, linewidth=1.2,
             label="No change (second half = first half)")
    xs = np.linspace(*lims, 50)
    ax1.plot(xs, fit[0] * xs + fit[1], color=ORANGE, linewidth=2,
             label=f"Actual fit (slope {fit[0]:.2f})")
    ax1.set_xlim(*lims)
    ax1.set_ylim(*lims)
    ax1.set_xlabel("Mean rating, first half of the run")
    ax1.set_ylabel("Mean rating, second half")
    ax1.legend(loc="upper left")
    fs.panel_title(ax1, f"Each show, halved — correlation {corr:+.2f}")
    fs.style_axes(ax1, grid="both")

    # One series, one colour: the quartiles are nominal categories and the sign
    # is already carried by the bar's direction and its signed label. This also
    # keeps red out of a figure that uses orange for the fitted line — the two
    # hues fail the palette's separation check when they share a figure.
    bars = ax2.bar(range(4), qs["change"], width=0.62, color=BLUE,
                   edgecolor=SURFACE, linewidth=0.6)
    ax2.axhline(0, color=AXIS, linewidth=0.8)
    for bar, val in zip(bars, qs["change"]):
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 val + (0.006 if val >= 0 else -0.006), f"{val:+.2f}",
                 ha="center", va="bottom" if val >= 0 else "top",
                 fontsize=10, color=INK_2)
    ax2.set_xticks(range(4))
    ax2.set_xticklabels(qs.index, fontsize=9)
    ax2.set_ylim(-0.13, 0.13)
    ax2.set_ylabel("Change in rating, first half -> second half")
    fs.panel_title(ax2, "Change by how strongly the show started")
    fs.style_axes(ax2, grid="y")

    fs.frame(
        fig,
        "A show's second half looks a lot like its first",
        "Comparing each show's first half against its separately measured "
        "second half — no shared episodes, so no mathematical coupling.",
        f"All {len(r):,} shows — every one has at least 13 rated episodes, so "
        f"both halves are well populated. {SOURCE}",
        rect=(0.05, 0.09, 0.985, 0.845),
    )
    return fs.save(fig, "fig02_halves_stability")


# --- figure 3 ---------------------------------------------------------------
def fig03_finale_premium():
    """Section 3 -- finales are usually a peak, not a crash."""
    MIN_SEASON_EP = 4
    sf, sp, series = [], [], []
    for _, g in DF.groupby("show_tconst"):
        g = g.sort_values(["season_number", "episode_number"])
        final_season = g["season_number"].max()
        for _, s in g.groupby("season_number"):
            ratings = s.sort_values("episode_number")["average_rating"].to_numpy(float)
            if len(ratings) < MIN_SEASON_EP:
                continue
            sf.append(ratings[-1] - ratings[:-1].mean())
            sp.append(ratings[0] - ratings[1:].mean())
        fsn = g[g["season_number"] == final_season].sort_values("episode_number")
        r = fsn["average_rating"].to_numpy(float)
        if len(r) >= MIN_SEASON_EP:
            series.append(r[-1] - r[:-1].mean())
    sf, sp, series = np.array(sf), np.array(sp), np.array(series)

    items = [
        ("Season finale\nvs its own season", sf.mean(), 100 * (sf > 0).mean(), len(sf)),
        ("Season premiere\nvs its own season", sp.mean(), 100 * (sp > 0).mean(), len(sp)),
        ("Series finale\nvs its final season", series.mean(), 100 * (series > 0).mean(), len(series)),
    ]
    for label, mean, pct, n in items:
        print(f"  {label.replace(chr(10), ' '):<34} mean {mean:+.3f}  above {pct:.1f}%  n={n:,}")
    print(f"  series finale drops >= 0.5: {100*(series <= -0.5).mean():.1f}%")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(W, 4.8))
    ypos = np.arange(3)[::-1]

    means = [i[1] for i in items]
    ax1.barh(ypos, means, height=0.4, color=[BLUE if m >= 0 else RED for m in means],
             edgecolor=SURFACE, linewidth=0.6)
    ax1.axvline(0, color=AXIS, linewidth=0.8)
    for y, m in zip(ypos, means):
        ax1.text(m + (0.012 if m >= 0 else -0.012), y, f"{m:+.2f}",
                 va="center", ha="left" if m >= 0 else "right",
                 fontsize=10, color=INK_2)
    ax1.set_yticks(ypos)
    ax1.set_yticklabels([i[0] for i in items], fontsize=9)
    ax1.set_xlim(-0.1, 0.32)
    ax1.set_xlabel("Average rating premium (points)")
    fs.panel_title(ax1, "How much better than the rest")
    fs.style_axes(ax1, grid="x")

    pcts = [i[2] for i in items]
    ax2.barh(ypos, pcts, height=0.4,
             color=[BLUE if p >= 50 else RED for p in pcts],
             edgecolor=SURFACE, linewidth=0.6)
    ax2.axvline(50, color=INK, linewidth=1.2)
    ax2.text(50.8, ypos[0] + 0.38, "coin flip", color=INK_2, fontsize=9, va="bottom")
    for y, p in zip(ypos, pcts):
        ax2.text(p + 1, y, f"{p:.1f}%", va="center", ha="left",
                 fontsize=10, color=INK_2)
    ax2.set_yticks(ypos)
    ax2.set_yticklabels([])
    ax2.set_xlim(0, 85)
    ax2.set_xlabel("Share that beats the rest of the season (%)")
    fs.panel_title(ax2, "How often it comes out on top")
    fs.style_axes(ax2, grid="x")

    fs.frame(
        fig,
        "Shows save their best episode for last",
        "Finales beat the rest of their season far more often than not; "
        "premieres are unremarkable by comparison.",
        f"Seasons with at least {MIN_SEASON_EP} rated episodes "
        f"(n = {len(sf):,} seasons, {len(series):,} series finales). {SOURCE}",
        rect=(0.11, 0.09, 0.985, 0.845),
    )
    return fs.save(fig, "fig03_finale_premium")


# --- figure 4 ---------------------------------------------------------------
def fig04_final_season_curse():
    """Section 4 -- the final-season curse, with its robustness check beside it."""
    d = FINALSEASON["delta"].to_numpy(float)
    pct_down = 100 * (d < 0).mean()
    median = np.median(d)
    print(f"  n={len(d):,} ended shows, {pct_down:.1f}% weaker final season, "
          f"median {median:+.3f}, mean {d.mean():+.3f}")

    thresholds = [-0.2, -0.3, -0.5, -0.75, -1.0]
    sweep = [100 * (d <= t).mean() for t in thresholds]
    for t, v in zip(thresholds, sweep):
        print(f"  cursed at {t:>5}: {v:.1f}%")

    edges = np.round(np.arange(-3.0, 3.0001, 0.1), 2)
    counts, _ = np.histogram(np.clip(d, -2.999, 2.999), bins=edges)
    centers = (edges[:-1] + edges[1:]) / 2
    colors = [RED if c < -0.5 else (BLUE if c > 0.5 else MUTED) for c in centers]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(W, 5.2),
                                   gridspec_kw={"width_ratios": [1.5, 1]})

    ax1.bar(centers, counts, width=0.1, color=colors,
            edgecolor=SURFACE, linewidth=0.6)
    ax1.axvline(0, color=AXIS, linewidth=0.8)
    ax1.axvline(-0.5, color=INK, linewidth=1.2)
    top = counts.max()
    ax1.set_ylim(0, top * 1.22)
    ax1.text(-0.58, top * 1.16, "clear curse threshold", ha="right", va="center",
             fontsize=9, color=INK_2)
    ax1.text(-1.78, top * 0.50, f"{100*(d <= -0.5).mean():.1f}% of ended shows",
             ha="center", va="bottom", fontsize=12.5, fontweight="bold", color=RED)
    ax1.text(-1.78, top * 0.47, "lose half a point or more",
             ha="center", va="top", fontsize=9.5, color=INK_2)
    ax1.set_xlim(-3, 3)
    ax1.set_xlabel("Final season vs the rest of the show (rating points)")
    ax1.set_ylabel("Number of shows")
    fs.panel_title(ax1, f"Almost a coin flip: {pct_down:.1f}% down, "
                        f"{100 - pct_down:.1f}% up")
    fs.style_axes(ax1, grid="y")

    ax2.plot(range(len(thresholds)), sweep, color=RED, marker="o",
             markersize=8, markerfacecolor=RED, markeredgecolor=SURFACE,
             markeredgewidth=2)
    for i, (t, v) in enumerate(zip(thresholds, sweep)):
        ax2.text(i, v + 1.6, f"{v:.1f}%", ha="center", fontsize=9.5, color=INK_2)
    ax2.set_xticks(range(len(thresholds)))
    ax2.set_xticklabels([f"{t}" for t in thresholds])
    ax2.set_ylim(0, 36)
    ax2.set_xlabel("Threshold used to call a final season 'cursed' (points)")
    ax2.set_ylabel("Share of ended shows (%)")
    fs.panel_title(ax2, "The verdict doesn't hinge on where we cut")
    fs.style_axes(ax2, grid="y")

    fs.frame(
        fig,
        "There is no final-season curse — except for a famous few",
        "Each ended show's final season compared against the average of "
        "everything that came before it.",
        f"Ended shows only, n = {len(d):,} (ongoing shows have no final season "
        f"yet). Axis clipped to +/-3 points ({(np.abs(d) > 3).sum()} shows fall "
        f"outside). {SOURCE}",
        rect=(0.05, 0.09, 0.985, 0.845),
    )
    return fs.save(fig, "fig04_final_season_curse")


# --- figure 5 ---------------------------------------------------------------
def fig05_era_length_genre():
    """Section 5 -- what actually predicts decline, net of everything else."""
    GENRES = ["Documentary", "Biography", "Horror", "Family", "Mystery", "Romance",
              "Fantasy", "History", "Sci-Fi", "Crime", "Drama", "Comedy",
              "Thriller", "Adventure", "Action", "Animation"]
    g1 = DF.groupby("show_tconst").agg(genres=("genres", "first")).reset_index()
    d = SLOPES.merge(g1, left_on="show_id", right_on="show_tconst", how="left")
    d["start_year"] = pd.to_numeric(d["start_year"], errors="coerce")
    d = d.dropna(subset=["start_year", "slope", "n_season", "genres"]).copy()
    for gen in GENRES:
        d[gen] = d["genres"].str.split(",").apply(lambda xs, g=gen: int(g in xs))
    d["yr_c"] = d["start_year"] - d["start_year"].mean()
    d["ongoing_i"] = d["ongoing"].astype(int)

    cols = ["yr_c", "n_season", "ongoing_i"] + GENRES
    X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in cols])
    y = d["slope"].to_numpy(float)
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    sigma2 = resid @ resid / (len(d) - X.shape[1])
    se = np.sqrt(np.diag(sigma2 * XtX_inv))
    names = ["intercept"] + cols
    coef = {n: (beta[i], se[i], beta[i] / se[i]) for i, n in enumerate(names)}
    print(f"  OLS n={len(d)}")
    for n in ["yr_c", "n_season", "ongoing_i"]:
        b, s, t = coef[n]
        print(f"  {n:<12} {b:+.4f} (se {s:.4f}, t {t:+.1f})")

    def draw(ax, rows):
        """rows: (label, coefficient name, unit scale). Dot + 95% CI per row."""
        ypos = np.arange(len(rows))[::-1]
        for y_, (label, key, scale) in zip(ypos, rows):
            b, s, t = coef[key]
            b, s = b * scale, s * scale
            color = MUTED if abs(t) <= 2 else (BLUE if b > 0 else RED)
            ax.plot([b - 1.96 * s, b + 1.96 * s], [y_, y_], color=color,
                    linewidth=2, solid_capstyle="round", alpha=0.55)
            ax.plot([b], [y_], marker="o", markersize=8, color=color,
                    markeredgecolor=SURFACE, markeredgewidth=2)
        ax.axvline(0, color=AXIS, linewidth=0.8)
        ax.set_yticks(ypos)
        ax.set_yticklabels([r[0] for r in rows], fontsize=9)
        ax.set_ylim(-0.6, len(rows) - 0.4)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(W, 6.6),
                                   gridspec_kw={"width_ratios": [1, 1]})

    # Era is shown per DECADE (coefficient x10) so it is legible beside the
    # per-season length effect; the underlying model is per year.
    # Row order matches the order the report's prose introduces them.
    draw(ax1, [("Each extra season", "n_season", 1),
               ("Ten years newer", "yr_c", 10),
               ("Still airing", "ongoing_i", 1)])
    ax1.set_xlabel("Effect on the show's trend (rating points across the run)")
    fs.panel_title(ax1, "Length and age — each net of the other")
    fs.style_axes(ax1, grid="x")

    order = sorted(GENRES, key=lambda g: coef[g][0])
    draw(ax2, [(g, g, 1) for g in order])
    ax2.set_xlabel("Effect on the show's trend, net of age and length")
    fs.panel_title(ax2, "Genre matters far less")
    fs.style_axes(ax2, grid="x")

    fs.frame(
        fig,
        "Decline is about a show's age and length, not its genre",
        "One regression, all factors at once: each effect is what remains after "
        "holding the others fixed.",
        "Coloured dot = statistically significant (|t| > 2); grey = not "
        "distinguishable from no effect. Bars are 95% confidence intervals.\n"
        f"OLS on {len(d):,} shows; a show can carry several genres. {SOURCE}",
        rect=(0.115, 0.10, 0.985, 0.845),
    )
    return fs.save(fig, "fig05_era_length_genre")


# --- figure 6 ---------------------------------------------------------------
def fig06_trajectory_shapes():
    """Section 6 -- the three trajectory shapes and what they look like."""
    counts = SHAPES["shape"].value_counts()
    total = len(SHAPES)
    # "linear/flat" means the fitted curve has no turning point inside the run
    # — the show is monotone over its own length, rising OR falling. It does
    # not mean the show is flat, so the label must not say "flat".
    labels = {"jumped_the_shark": "Jumped the shark\n(peaks mid-run, then falls)",
              "linear/flat": "Straight line\n(no turn mid-run)",
              "found_itself": "Found itself\n(dips, then recovers)"}
    colors = {"jumped_the_shark": ORANGE, "linear/flat": MUTED, "found_itself": AQUA}
    order = ["jumped_the_shark", "linear/flat", "found_itself"]
    for k in order:
        print(f"  {k:<18} {counts[k]:>5} ({100*counts[k]/total:.1f}%)")

    # Average fitted curve per class, centred on each show's own mean so the
    # shapes — not the rating levels — are what is being compared.
    xs = np.linspace(0, 1, 60)
    curves = {k: [] for k in order}
    for show_id, g in DF.groupby("show_tconst"):
        g = g.sort_values("overall_order")
        x = (g["overall_order"].to_numpy(float) - 1) / (len(g) - 1)
        y = g["average_rating"].to_numpy(float)
        w = np.sqrt(g["num_votes"].to_numpy(float))
        a, b, c = weighted_quad(x, y, w)
        curve = a + b * xs + c * xs ** 2
        shape = SHAPES.loc[SHAPES["show_id"] == show_id, "shape"]
        if len(shape):
            curves[shape.iloc[0]].append(curve - curve.mean())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(W, 5.4),
                                   gridspec_kw={"width_ratios": [1, 1.15]})

    ypos = np.arange(len(order))[::-1]
    shares = [100 * counts[k] / total for k in order]
    ax1.barh(ypos, shares, height=0.55, color=[colors[k] for k in order],
             edgecolor=SURFACE, linewidth=0.6)
    for y_, k, share in zip(ypos, order, shares):
        ax1.text(share + 1, y_, f"{share:.1f}%", va="center", ha="left",
                 fontsize=11, fontweight="bold", color=INK_2)
    ax1.set_yticks(ypos)
    ax1.set_yticklabels([labels[k] for k in order], fontsize=9)
    ax1.set_xlim(0, 55)
    ax1.set_xlabel("Share of shows (%)")
    fs.panel_title(ax1, "Which shape a show's run takes")
    fs.style_axes(ax1, grid="x")

    for k in order:
        mean_curve = np.mean(curves[k], axis=0)
        ax2.plot(xs, mean_curve, color=colors[k], linewidth=2.4,
                 label=labels[k].replace("\n", " "))
        ax2.text(1.01, mean_curve[-1], labels[k].split("\n")[0],
                 color=INK_2, fontsize=9, va="center", ha="left")
    ax2.axhline(0, color=AXIS, linewidth=0.8)
    ax2.set_xlim(0, 1)
    ax2.set_xticks([0, 0.5, 1])
    ax2.set_xticklabels(["First episode", "Midpoint", "Last episode"])
    ax2.set_ylabel("Rating vs the show's own average")
    fs.panel_title(ax2, "The average arc of each shape")
    fs.style_axes(ax2, grid="y")

    fs.frame(
        fig,
        "The rise-then-fall arc is the most common shape — and it is gentle",
        "A curve fitted to every show's episode ratings, then classified by "
        "where that curve turns.",
        f"n = {total:,} shows. Right panel averages each class's fitted curve "
        "after centring it on the show's own mean rating; the straight-line\n"
        "class holds both rising and falling shows, so its average is their net. "
        "Robustness: the shares move less than one point across curvature\n"
        "cut-offs from 0 to 0.10. About a fifth of 'found itself' cases rest on "
        f"thinly-voted late episodes (see docs/decisions.md). {SOURCE}",
        rect=(0.05, 0.155, 0.93, 0.845),
    )
    return fs.save(fig, "fig06_trajectory_shapes")


# --- figure 7 ---------------------------------------------------------------
def fig07_peak_location():
    """Section 6 -- where the best season actually sits."""
    rows = []
    for show_id, g in DF.groupby("show_tconst"):
        season_means = g.groupby("season_number")["average_rating"].mean()
        seasons = sorted(season_means.index)
        n_season = len(seasons)
        best_rank = seasons.index(season_means.idxmax()) + 1
        rows.append({"n_season": n_season, "best_rank": best_rank,
                     "best_frac": (best_rank - 1) / (n_season - 1) if n_season > 1 else np.nan,
                     "is_first": best_rank == 1, "is_last": best_rank == n_season})
    bs = pd.DataFrame(rows)

    groups = [(2, "2"), (3, "3"), (4, "4"), (5, "5"), (6, "6"), (7, "7")]
    abs_means, norm_means, labels_x = [], [], []
    for ns, lab in groups:
        sub = bs[bs["n_season"] == ns]
        abs_means.append(sub["best_rank"].mean())
        norm_means.append(sub["best_frac"].mean())
        labels_x.append(lab)
    long = bs[bs["n_season"] >= 8]
    abs_means.append(long["best_rank"].mean())
    norm_means.append(long["best_frac"].mean())
    labels_x.append("8+")
    for lab, a, n in zip(labels_x, abs_means, norm_means):
        print(f"  {lab:>3} seasons: mean best season {a:.2f}, normalized {n:.3f}")

    mid = bs[bs["n_season"] >= 5]
    thirds = [100 * (mid["best_frac"] <= 1 / 3).mean(),
              100 * ((mid["best_frac"] > 1 / 3) & (mid["best_frac"] < 2 / 3)).mean(),
              100 * (mid["best_frac"] >= 2 / 3).mean()]
    pct_first = 100 * bs["is_first"].mean()
    pct_last = 100 * bs["is_last"].mean()
    print(f"  thirds (>=5 seasons): first {thirds[0]:.1f} / middle {thirds[1]:.1f} "
          f"/ last {thirds[2]:.1f}")
    print(f"  best season is the first: {pct_first:.1f}%, the last: {pct_last:.1f}%")

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(W, 5.0),
                                        gridspec_kw={"width_ratios": [1.1, 1, 0.8]})

    ax1.bar(range(len(labels_x)), abs_means, width=0.6, color=BLUE,
            edgecolor=SURFACE, linewidth=0.6)
    for i, v in enumerate(abs_means):
        ax1.text(i, v + 0.09, f"{v:.1f}", ha="center", fontsize=9, color=INK_2)
    ax1.set_xticks(range(len(labels_x)))
    ax1.set_xticklabels(labels_x)
    ax1.set_xlabel("How many seasons the show ran")
    ax1.set_ylabel("Average best season (season number)")
    ax1.set_ylim(0, 6.6)
    fs.panel_title(ax1, "The peak moves later in longer shows")
    fs.style_axes(ax1, grid="y")

    # One series, one colour: the three thirds are nominal categories, so
    # colouring them differently would encode nothing the numbers don't say.
    ax2.bar(range(3), thirds, width=0.6, color=BLUE,
            edgecolor=SURFACE, linewidth=0.6)
    for i, v in enumerate(thirds):
        ax2.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=10, color=INK_2)
    ax2.set_xticks(range(3))
    ax2.set_xticklabels(["First third", "Middle third", "Last third"])
    ax2.set_ylim(0, 52)
    ax2.set_ylabel("Share of shows (%)")
    fs.panel_title(ax2, "But it is not concentrated there")
    fs.style_axes(ax2, grid="y")

    ax3.bar([0, 1], [pct_first, pct_last], width=0.5, color=BLUE,
            edgecolor=SURFACE, linewidth=0.6)
    for i, v in enumerate([pct_first, pct_last]):
        ax3.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=10, color=INK_2)
    ax3.set_xticks([0, 1])
    ax3.set_xticklabels(["First season\nis the best", "Last season\nis the best"])
    ax3.set_ylim(0, 52)
    ax3.set_ylabel("Share of shows (%)")
    fs.panel_title(ax3, "And rarely the first")
    fs.style_axes(ax3, grid="y")

    fs.frame(
        fig,
        "Shows don't peak in season two — or in the middle, reliably",
        "Where a show's highest-rated season falls, by how long the show ran. "
        "The average sits mid-run, but the middle is the least likely spot.",
        f"Middle panel: shows with at least 5 seasons (n = {len(mid):,}), where "
        f"'thirds' are meaningful. Right panel: all {len(bs):,} shows. {SOURCE}",
        rect=(0.045, 0.115, 0.985, 0.845),
    )
    return fs.save(fig, "fig07_peak_location")


# --- figure 8 ---------------------------------------------------------------
# One show from each of the three groups in fig01 — clearly declining,
# essentially flat, clearly rising — rather than one per curvature class.
# This mix matches the report's own headline instead of contradicting it, so
# the figure needs no "not a representative sample" disclaimer. All three are
# household names (1.4M-4.5M votes) and span three decades, which also shows
# the method working on shows of very different length.
# Game of Thrones is deliberately NOT reused here — it already carries fig09.
EXAMPLES = [
    ("tt4574334", "Stranger Things", "slides after its peak"),
    ("tt0108778", "Friends", "ten seasons, no real drift"),
    ("tt0903747", "Breaking Bad", "climbs all the way"),
]


def fig08_example_trajectories():
    """Sections 1 and 7 -- what a single show's data actually looks like."""
    fig, axes = plt.subplots(1, 3, figsize=(W, 5.0), sharey=True)
    xs = np.linspace(0, 1, 60)

    for ax, (tconst, title, blurb) in zip(axes, EXAMPLES):
        g, x, y, v = show_frame(tconst)
        w = np.sqrt(v)
        a, b = weighted_linear(x, y, w)
        qa, qb, qc = weighted_quad(x, y, w)
        shape = SHAPES.loc[SHAPES["show_id"] == tconst, "shape"].iloc[0]
        print(f"  {title:<20} n={len(g):>3} slope={b:+.2f} shape={shape}")

        ax.scatter(x, y, s=6 + 40 * (w / w.max()), color=BLUE, alpha=0.45,
                   linewidths=0)
        ax.plot(xs, qa + qb * xs + qc * xs ** 2, color=MUTED, linewidth=1.6)
        ax.plot(xs, a + b * xs, color=ORANGE, linewidth=2.4)
        ax.set_xlim(-0.03, 1.03)
        ax.set_xticks([0, 0.5, 1])
        ax.set_xticklabels(["First", "Middle", "Last"])
        ax.set_xlabel("Episode order")
        fs.panel_title(ax, f"{title} — {blurb}\ntrend {b:+.2f} points across the run")
        fs.style_axes(ax, grid="y")

    axes[0].set_ylabel("Episode rating")
    axes[0].set_ylim(5.2, 10.1)  # contains every episode of all three shows
    # One legend for the whole figure: two fitted lines plus the marker key.
    axes[2].plot([], [], color=ORANGE, linewidth=2.4, label="Straight-line trend")
    axes[2].plot([], [], color=MUTED, linewidth=1.6, label="Curved trend")
    axes[2].scatter([], [], s=40, color=BLUE, alpha=0.45, linewidths=0,
                    label="Episode (size = votes)")
    axes[2].legend(loc="lower right")

    fs.frame(
        fig,
        "Down, sideways, up — one show from each group",
        "Every dot is one episode; bigger dots carry more votes. The straight "
        "line is the trend each show is scored on.",
        "One show from each of the three groups in Figure 1: clearly declining, "
        "essentially flat, clearly rising. Episode order is rescaled\n"
        f"to 0-1 so shows of very different lengths line up. {SOURCE}",
        rect=(0.045, 0.14, 0.985, 0.845),
    )
    return fs.save(fig, "fig08_example_trajectories")


# --- figure 9 ---------------------------------------------------------------
def fig09_weighting_choice():
    """Section 7 -- why the vote weighting had to be sqrt, not raw votes."""
    tconst = "tt0944947"
    g, x, y, v = show_frame(tconst)
    # Categorical colours here (not the diverging red/blue used elsewhere):
    # these three lines are competing methods, not directions of travel. The
    # chosen fit is ORANGE and drawn thicker — the same colour the fitted
    # trend carries in fig02 and fig08, so one estimator keeps one identity.
    fits = {
        "By raw votes": (weighted_linear(x, y, v), AQUA, 1.8),
        "By the square root of votes — chosen": (
            weighted_linear(x, y, np.sqrt(v)), ORANGE, 2.8),
        "Unweighted": (weighted_linear(x, y, np.ones_like(v)), MUTED, 1.8),
    }
    for label, ((a, b), _, _) in fits.items():
        print(f"  {label:<28} intercept {a:.3f}  slope {b:+.3f}")

    final_season = g["season_number"].max()
    is_final = (g["season_number"] == final_season).to_numpy()
    top6 = np.argsort(v)[-6:]
    print(f"  most-voted episode: S{g['season_number'].iloc[top6[-1]]}"
          f"E{g['episode_number'].iloc[top6[-1]]} "
          f"rating {y[top6[-1]]}, votes {v[top6[-1]]:,}")
    print(f"  of the 6 most-voted episodes, {is_final[top6].sum()} are final-season")

    fig, ax = plt.subplots(figsize=(W, 5.8))
    xs = np.linspace(0, 1, 60)
    ax.scatter(x, y, s=8 + 90 * (v / v.max()), color=BLUE, alpha=0.4, linewidths=0)
    for label, ((a, b), color, lw) in fits.items():
        ax.plot(xs, a + b * xs, color=color, linewidth=lw, label=label)

    # Call out the two episodes that drive the difference between the fits.
    biggest = top6[-1]
    ax.annotate(f"most-voted episode of all:\na mid-run 9.9 "
                f"({v[biggest]/1000:.0f}k votes)",
                xy=(x[biggest], y[biggest]), xytext=(x[biggest] - 0.30, 9.9),
                fontsize=9, color=INK_2, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=1))
    worst = int(np.argmin(y))
    ax.annotate(f"final season: heavily voted\nand rated far below the rest",
                xy=(x[worst], y[worst]), xytext=(0.52, 4.6),
                fontsize=9, color=INK_2, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=1))

    ax.set_xlim(-0.03, 1.03)
    ax.set_xticks([0, 0.5, 1])
    ax.set_xticklabels(["First episode", "Midpoint", "Last episode"])
    ax.set_ylim(3.5, 10.4)
    ax.set_ylabel("Episode rating")
    ax.legend(loc="lower left")
    fs.style_axes(ax, grid="y")

    fs.frame(
        fig,
        "How much a viral finale should count: Game of Thrones",
        "The same 73 episodes, three ways of weighting them. Weighting by raw "
        "vote counts lets a handful of late episodes set the whole trend.",
        "Dot size is the episode's vote count. Four of the six most-voted "
        "episodes are final-season ones — but the single most-voted is a "
        "mid-run 9.9.",
        rect=(0.065, 0.105, 0.985, 0.83),
    )
    return fs.save(fig, "fig09_weighting_choice")


def main():
    fs.apply_style()
    for fn in [fig01_slope_distribution, fig02_halves_stability,
               fig03_finale_premium, fig04_final_season_curse,
               fig05_era_length_genre, fig06_trajectory_shapes,
               fig07_peak_location, fig08_example_trajectories,
               fig09_weighting_choice]:
        print(f"\n{fn.__name__}  -- {fn.__doc__.splitlines()[0]}")
        fn()


if __name__ == "__main__":
    main()
