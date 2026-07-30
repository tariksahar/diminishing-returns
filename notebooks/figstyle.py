"""Shared figure style for the report figures (Phase 3).

Colours come from the validated data-viz reference palette. The palette was
re-validated for this project with a Python port of the skill's checker
(lightness band, chroma floor, Machado-2009 protan/deutan CVD separation,
normal-vision floor, WCAG contrast vs the chart surface):

  - categorical trio  #2a78d6 / #eb6834 / #1baf7a  -> passes all-pairs
    (worst CVD dE 9.2, worst normal-vision dE 24.0)
  - diverging poles   #2a78d6 (rise) / #e34948 (decline) -> passes
    (worst CVD dE 21.6, normal-vision dE 32.3)

Two deliberate deviations from the palette defaults, both documented there:
  - AQUA sits at 2.74:1 against the surface (below the 3:1 line). The palette's
    "relief rule" allows this when the mark carries a visible direct label, so
    every aqua mark in these figures is directly labelled.
  - MUTED grey is used for de-emphasis (the "flat" middle of a diverging scale,
    statistically insignificant coefficients). It fails the categorical chroma
    floor by construction -- it is an ink token, not a series colour, and never
    carries an identity on its own.
"""

import sys

import matplotlib as mpl
import matplotlib.pyplot as plt

# --- palette -----------------------------------------------------------------
# Two validated sets of the same eight roles. The dark column is the reference
# palette's own dark steps, not an inversion: re-checked against the dark
# surface (#1a1a19) with the same Python port of the checker, where the trio
# blue/orange/aqua passes all-pairs (worst CVD dE 9.4, normal-vision 20.9) and
# the diverging poles pass at dE 19.2 / 29.0. The orange-red clash documented
# below survives in dark mode too (normal-vision dE 7.1), so the role rule is
# mode-independent.
_LIGHT = {
    "SURFACE": "#fcfcfb", "INK": "#0b0b0b", "INK_2": "#52514e",
    "MUTED": "#898781", "GRID": "#e1e0d9", "AXIS": "#c3c2b7",
    "BLUE": "#2a78d6", "ORANGE": "#eb6834", "AQUA": "#1baf7a", "RED": "#e34948",
}
_DARK = {
    "SURFACE": "#1a1a19", "INK": "#ffffff", "INK_2": "#c3c2b7",
    "MUTED": "#898781", "GRID": "#2c2c2a", "AXIS": "#383835",
    "BLUE": "#3987e5", "ORANGE": "#d95926", "AQUA": "#199e70", "RED": "#e66767",
}

# The flag is read here, at import time, because phase3_figures.py binds these
# names with `from figstyle import BLUE, ...` before any function runs. Paper
# plates are always light: they go into a PDF, which has no theme.
DARK = "--dark" in sys.argv and "--paper" not in sys.argv
_P = _DARK if DARK else _LIGHT

SURFACE = _P["SURFACE"]  # chart surface
INK = _P["INK"]          # primary text
INK_2 = _P["INK_2"]      # secondary text
MUTED = _P["MUTED"]      # axis labels, de-emphasised marks
GRID = _P["GRID"]        # hairline gridlines
AXIS = _P["AXIS"]        # baseline / axis rule

BLUE = _P["BLUE"]        # categorical slot 1 / diverging "rise" pole
ORANGE = _P["ORANGE"]    # categorical slot 2
AQUA = _P["AQUA"]        # categorical slot 3 (always direct-labelled, see above)
RED = _P["RED"]          # diverging "decline" pole

# Semantic aliases so the figure code reads in the language of the analysis.
RISE, DECLINE, FLAT = BLUE, RED, MUTED

# HARD RULE: ORANGE and RED must never appear in the same figure. They fail the
# separation checks against each other -- CVD dE 5.6 (floor 6.0) and, worse,
# normal-vision dE 7.1 against a floor of 15, so readers with full colour
# vision cannot reliably tell them apart either. Every other pair in use here
# clears both floors. Roles are assigned so the two never meet:
#   BLUE    single series / data points, and the "rise" pole of the diverging scale
#   RED     the "decline" pole -- only in figures with no orange
#   ORANGE  the fitted trend line the analysis actually uses (fig02, fig08, fig09)
#   AQUA    a rejected alternative or a third class -- always directly labelled,
#           since it sits below the 3:1 contrast line (relief rule)
#   MUTED   de-emphasis: neutral reference lines, the flat middle of a diverging
#           scale, statistically insignificant estimates


# --- output mode ---------------------------------------------------------------
# The essay and the technical report want different figures from the same data.
# ESSAY mode: editorial charts that stand alone on a web page -- headline, subtitle
#   and source note baked in, drawn on the palette's off-white surface.
# PAPER mode: plates for a LaTeX document. The caption below the figure does the
#   naming and the caveats, so the in-image title block is dropped; the surface
#   becomes pure white so the figure does not read as a grey pasted-in block; and
#   the canvas is halved so that, once scaled into a 14 cm text column, the labels
#   land at roughly body-text size instead of ~4 pt.
PAPER = False


def apply_style(paper=False):
    """Set the global rcParams. Call once, before creating any figure."""
    global PAPER
    PAPER = paper
    surface = "#ffffff" if paper else SURFACE
    mpl.rcParams.update({
        "figure.facecolor": surface,
        "axes.facecolor": surface,
        "savefig.facecolor": surface,
        "savefig.dpi": 200,
        "figure.dpi": 110,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "font.size": 9.5,
        "axes.titlesize": 10.5,
        "axes.labelsize": 9.5,
        "axes.labelcolor": INK_2,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_2,
        "ytick.labelcolor": INK_2,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.frameon": False,
        "legend.fontsize": 9,
        # Solid hairline grid, always behind the marks (never dashed).
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "axes.axisbelow": True,
        "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
    })


def style_axes(ax, grid="y"):
    """Strip the box down to two hairline rules and one recessive grid axis.

    grid: "y" (horizontal lines, for column charts), "x" (for bar charts),
          "both", or None.
    """
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(length=0)
    if grid in ("y", "both"):
        ax.grid(axis="y", which="major")
    if grid in ("x", "both"):
        ax.grid(axis="x", which="major")
    if grid is None:
        ax.grid(False)
    return ax


def panel_title(ax, text):
    """Small left-aligned panel heading (used inside multi-panel figures).

    Note: matplotlib keeps a separate title object per location, so this must
    set (and any restyling must read) loc="left" -- a bare ax.get_title()
    returns the *centre* title and silently wipes this one.
    """
    ax.set_title(text, loc="left", color=INK_2, fontsize=10, pad=8)


def frame(fig, title, subtitle=None, footnote=None, rect=(0.055, 0.085, 0.985, 0.855)):
    """Lay out the figure with an editorial left-aligned title block.

    The title block and footnote live in figure coordinates, so `rect` reserves
    the space for them; matplotlib's tight_layout then packs the axes inside.

    In PAPER mode the title block is not drawn at all -- the LaTeX caption names
    the figure and carries its caveats -- so the axes take the reclaimed space.
    Callers pass the same arguments either way; only the rendering differs.
    """
    if PAPER:
        left, _, right, _ = rect
        fig.tight_layout(rect=[left, 0.02, right, 0.98])
        return
    fig.tight_layout(rect=list(rect))
    fig.text(0.055, 0.955, title, ha="left", va="top",
             fontsize=13.5, fontweight="bold", color=INK)
    if subtitle:
        fig.text(0.055, 0.897, subtitle, ha="left", va="top",
                 fontsize=10, color=INK_2)
    if footnote:
        fig.text(0.055, 0.028, footnote, ha="left", va="bottom",
                 fontsize=8, color=MUTED)


def save(fig, name):
    """Write to figures/, or figures/paper/, or figures/dark/ by mode."""
    import os
    folder = "figures/paper" if PAPER else ("figures/dark" if DARK else "figures")
    os.makedirs(folder, exist_ok=True)
    path = f"{folder}/{name}.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  saved {path}")
    return path
