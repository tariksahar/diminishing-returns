"""Draw the 1280x640 card that link previews show for this project.

Every surface that shares this project -- the GitHub repository preview, the
Pages site's og:image, and therefore every post on any platform that unfurls a
link -- renders one image. Left alone it is GitHub's generic auto-generated
card, which shows the repository name and nothing about the finding.

The numbers are recomputed here from `data/processed/`, not typed in, for the
same reason the report figures recompute theirs: a card is a published claim,
and a published claim that cannot go stale is worth the extra ten lines.

Colours come from the validated palette in notebooks/figstyle.py. The bar uses
the diverging trio RED / MUTED / BLUE, which is the pairing that palette
validated for exactly this role (decline pole, flat middle, rise pole).

Run from the repository root:

    python src/social_card.py            -> assets/social-card.png
"""

import json
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, "notebooks")
import figstyle as fs  # noqa: E402

SLOPES = "data/processed/_phase2_slopes_full.json"
OUT = "assets/social-card.png"
CLEAR = 0.5  # the clear-decline / clear-rise threshold, as everywhere else

# 1280x640 is the size GitHub and every major unfurler crop to. Drawing at
# exactly that size means nothing is resampled.
WIDTH_PX, HEIGHT_PX = 1280, 640
DPI = 100


def three_way_split():
    """The headline split and the population, recomputed rather than typed."""
    rows = json.load(open(SLOPES, encoding="utf-8"))
    slopes = [row["slope"] for row in rows]
    n_shows = len(slopes)
    n_episodes = sum(row["n_ep"] for row in rows)
    decline = sum(1 for s in slopes if s <= -CLEAR)
    rise = sum(1 for s in slopes if s >= CLEAR)
    # Counted, never derived as `n - decline - rise`: the same complementary
    # -share mistake this project has already made twice.
    flat = sum(1 for s in slopes if -CLEAR < s < CLEAR)
    assert decline + flat + rise == n_shows, "the three bands must partition the shows"
    return (n_shows, n_episodes,
            100 * decline / n_shows, 100 * flat / n_shows, 100 * rise / n_shows)


def draw():
    n_shows, n_episodes, pct_decline, pct_flat, pct_rise = three_way_split()

    fig = plt.figure(figsize=(WIDTH_PX / DPI, HEIGHT_PX / DPI), dpi=DPI)
    fig.patch.set_facecolor(fs._LIGHT["SURFACE"])
    ink, ink2, muted = fs._LIGHT["INK"], fs._LIGHT["INK_2"], fs._LIGHT["MUTED"]

    # A single full-bleed axes in figure coordinates: this is a poster, not a
    # plot, so nothing is left to a layout engine.
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.062, 0.880, "Do TV shows really decline?",
            fontsize=44, fontweight="bold", color=ink, va="top", ha="left")
    ax.text(0.062, 0.735,
            f"{n_episodes:,} episode ratings  ·  {n_shows:,} shows  ·  "
            "one straight question",
            fontsize=19, color=ink2, va="top", ha="left")

    # --- the split, as one stacked rule --------------------------------------
    bar_left, bar_right = 0.062, 0.938
    bar_y, bar_h = 0.300, 0.115
    span = bar_right - bar_left

    segments = [
        (pct_decline, fs._LIGHT["RED"], "decline"),
        (pct_flat, fs._LIGHT["MUTED"], "flat"),
        (pct_rise, fs._LIGHT["BLUE"], "rise"),
    ]

    x = bar_left
    for pct, colour, label in segments:
        w = span * pct / 100
        ax.add_patch(Rectangle((x, bar_y), w, bar_h,
                               facecolor=colour, edgecolor="none"))
        # The label sits inside its own segment, so no legend is needed and no
        # colour has to be identified by hue alone.
        ax.text(x + w / 2, bar_y + bar_h / 2, f"{pct:.1f}%",
                fontsize=17, fontweight="bold", color="#ffffff",
                ha="center", va="center")
        ax.text(x + w / 2, bar_y - 0.052, label,
                fontsize=15, color=ink2, ha="center", va="top")
        x += w

    ax.text(0.062, 0.550,
            "Only about one in six clearly declines. More rise than fall.",
            fontsize=24, fontweight="bold", color=ink, va="top", ha="left")

    ax.text(0.062, 0.075,
            "IMDb episode ratings  ·  full essay, technical report and code at "
            "tariksahar.github.io/diminishing-returns",
            fontsize=13.5, color=muted, va="bottom", ha="left")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  saved {OUT}  ({WIDTH_PX}x{HEIGHT_PX})")
    print(f"  split recomputed: {pct_decline:.1f} / {pct_flat:.1f} / {pct_rise:.1f}")


if __name__ == "__main__":
    draw()
