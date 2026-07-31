"""Lints on the technical report's two sources, and on their agreement.

There is no LaTeX toolchain on this machine, so `technical_report.tex` is
compiled by hand on Overleaf and every mistake in it costs a manual round trip.
Two rounds were spent on faults that a few lines of parsing would have caught,
so they are caught here instead:

  * a `\\label` placed after a `\\paragraph` inherits the enclosing SECTION
    number, so two such labels in one section both render as "Section 5". A
    sentence that referenced one of each read "Section 5 examines X. (The sweep
    in Section 5 is a different quantity.)" -- self-contradictory in the PDF and
    perfectly sensible in the source.
  * the report exists as both `.tex` and `.md`, one document in two formats, and
    nothing checked that they quote the same numbers.

Run from the repository root:  pytest
"""

import re
from pathlib import Path

import pytest

TEX = Path("docs/technical_report.tex")
MD = Path("docs/technical_report.md")


@pytest.fixture(scope="module")
def tex():
    return TEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def md():
    return MD.read_text(encoding="utf-8")


def test_every_ref_and_cite_resolves(tex):
    """An undefined \\ref compiles to '??' and is easy to miss in a 16-page PDF."""
    labels = set(re.findall(r"\\label\{([^}]+)\}", tex))
    bibitems = set(re.findall(r"\\bibitem\{([^}]+)\}", tex))

    missing_refs = set(re.findall(r"\\ref\{([^}]+)\}", tex)) - labels
    # \cite takes a comma-separated list, e.g. \cite{spearman,brown}.
    cited = {k.strip()
             for group in re.findall(r"\\cite\{([^}]+)\}", tex)
             for k in group.split(",")}
    missing_cites = cited - bibitems
    assert not missing_refs, f"undefined \\ref targets: {sorted(missing_refs)}"
    assert not missing_cites, f"undefined \\cite keys: {sorted(missing_cites)}"


def test_no_orphan_bibitems(tex):
    """A reference nobody cites is padding, and reviewers notice."""
    bibitems = set(re.findall(r"\\bibitem\{([^}]+)\}", tex))
    cited = set()
    for group in re.findall(r"\\cite\{([^}]+)\}", tex):
        cited.update(k.strip() for k in group.split(","))
    assert not (bibitems - cited), f"uncited references: {sorted(bibitems - cited)}"


def test_paragraph_labels_are_not_referenced_as_sections(tex):
    """`\\paragraph` produces no number, so a label under one resolves to the
    enclosing section. Referencing it as "Section~\\ref{...}" therefore prints a
    number that does not identify the thing being pointed at -- and two of them
    in the same sentence print the same number."""
    paragraph_labels = set(
        re.findall(r"\\paragraph\{[^}]*\}\s*\n\\label\{([^}]+)\}", tex)
    )
    offenders = sorted(
        lbl for lbl in paragraph_labels
        if re.search(r"Section~\\ref\{" + re.escape(lbl) + r"\}", tex)
    )
    assert not offenders, (
        "these labels sit on \\paragraph (unnumbered) but are cited as "
        f"'Section~\\ref': {offenders}. Name the paragraph in the prose, or "
        "promote it to a \\subsection so it has a number of its own."
    )


# The claims that must read identically in both formats. Kept to figures a
# reader would compare, not every number in the paper.
SHARED_NUMBERS = [
    "16.9", "57.4", "25.7",       # the headline split
    "50.5", "49.2", "12.6",       # the final-season split
    "72.6", "71.6",               # the finale premia
    "43.3", "23.8",               # the two fame gradients
    "15.6", "60.4", "23.9",       # the noise-corrected split
    "0.189", "0.4238", "21.9",    # the estimation-error section
    "2.96", "0.0031",             # the multiplicity threshold
    "0.0603",                     # model fit
]


@pytest.mark.parametrize("number", SHARED_NUMBERS)
def test_the_two_formats_quote_the_same_numbers(tex, md, number):
    """One document, two files. A number corrected in one and forgotten in the
    other is the failure this guards -- it has happened, in both directions."""
    assert number in tex, f"{number} is in the .md but missing from the .tex"
    assert number in md, f"{number} is in the .tex but missing from the .md"


def test_the_withdrawn_biography_claim_stays_withdrawn(tex, md):
    """Biography clears the raw 5% bar but no correction, so both formats must
    say so rather than listing it as an effect."""
    for name, source in (("tex", tex), ("md", md)):
        assert "Biography" in source, f"{name}: Biography should still be discussed"
        assert re.search(r"Biography.{0,200}(survives neither|neither correction)",
                         source, re.S), (
            f"{name}: Biography is named but no longer marked as surviving "
            "neither correction"
        )
