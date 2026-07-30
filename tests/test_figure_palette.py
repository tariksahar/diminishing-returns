"""The palette rules figstyle.py states in prose, enforced.

figstyle.py carries a "HARD RULE: ORANGE and RED must never appear in the same
figure" -- they separate by only dE 5.6 under simulated deutan vision and dE
7.1 under normal vision, against floors of 6.0 and 15. A comment cannot stop
anyone breaking it, and the first version of fig02 did break it: an orange
fitted line beside red quartile bars, caught by hand.

This reads notebooks/phase3_figures.py as a syntax tree and checks each figure
function's colour usage. Static rather than rendered, so it cannot see a colour
reached indirectly -- but every figure names its colours directly today, which
is exactly the habit worth locking in.

Run from the repository root:  pytest
"""

import ast
import re
from pathlib import Path

import pytest

FIGURES_SOURCE = Path("notebooks/phase3_figures.py")
FIGURE_NAME = re.compile(r"^fig\d{2}_")


def colour_names_used(node):
    """Every palette token referenced inside a function, whether imported bare
    (ORANGE) or reached through the module (fs.ORANGE)."""
    palette = {"BLUE", "ORANGE", "AQUA", "RED", "MUTED",
               "RISE", "DECLINE", "FLAT"}
    used = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in palette:
            used.add(child.id)
        elif isinstance(child, ast.Attribute) and child.attr in palette:
            used.add(child.attr)
    return used


@pytest.fixture(scope="module")
def figure_functions():
    tree = ast.parse(FIGURES_SOURCE.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and FIGURE_NAME.match(node.name)
    }
    assert len(functions) == 9, f"expected nine figure functions, found {len(functions)}"
    return functions


def test_orange_and_red_never_share_a_figure(figure_functions):
    offenders = []
    for name, node in figure_functions.items():
        used = colour_names_used(node)
        # DECLINE is an alias of RED, so it counts as red for this rule.
        reds = used & {"RED", "DECLINE"}
        if "ORANGE" in used and reds:
            offenders.append(f"{name} uses ORANGE with {sorted(reds)}")
    assert not offenders, (
        "ORANGE and RED are indistinguishable to many readers and must not "
        "appear together:\n  " + "\n  ".join(offenders)
    )


def test_the_palette_constants_are_the_validated_ones(figure_functions):
    """The hex values that passed the colour-blind and contrast checks. Changing
    one means re-running that validation, not editing this list."""
    import sys
    sys.path.insert(0, "notebooks")
    import figstyle

    assert figstyle._LIGHT["BLUE"] == "#2a78d6"
    assert figstyle._LIGHT["ORANGE"] == "#eb6834"
    assert figstyle._LIGHT["AQUA"] == "#1baf7a"
    assert figstyle._LIGHT["RED"] == "#e34948"
    assert figstyle._DARK["BLUE"] == "#3987e5"
    assert figstyle._DARK["ORANGE"] == "#d95926"
    assert figstyle._DARK["AQUA"] == "#199e70"
    assert figstyle._DARK["RED"] == "#e66767"


def test_paper_mode_never_renders_dark(figure_functions):
    """The paper plates go into a PDF, which has no theme. figstyle guarantees
    this by construction; the guarantee is worth a test because --dark and
    --paper are both plain argv flags and easy to combine by accident."""
    import sys
    sys.path.insert(0, "notebooks")
    import figstyle

    source = Path("notebooks/figstyle.py").read_text(encoding="utf-8")
    assert '"--dark" in sys.argv and "--paper" not in sys.argv' in source
    assert figstyle.DARK is False  # pytest is not run with --dark
