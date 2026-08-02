"""The deliberately bad figure for Exercise 21.2.

Nothing here is broken. The script runs, the numbers are real, and the picture
it draws is wrong in five specific ways. The five are written down here so that
the exercise has one reproducible answer instead of an argument.

  1. Neither axis is labeled. Nothing on the figure says what is being
     measured or in what units, so the numbers up the side mean nothing.
  2. The bars are red and green, which is the one pair of colors that the
     commonest form of color vision deficiency collapses into each other.
  3. The y axis starts at 18 rather than 0, and no part of the figure says so.
     A six percent difference between the group means becomes a cliff.
  4. The legend labels the two colors virgin and pregnant. The samples are
     virgin and lactating. There is no pregnant sample in this figure at all.
  5. The caption states that lactation halves Brca1. The group means are
     20.5 and 19.3 counts per million, so the figure does not support it.

The four values are Brca1 in the four luminal samples of GSE60450, in counts
per million, computed the same way as everywhere else in the book.

    MPLBACKEND=Agg .venv/bin/python scripts/ch21_bad_figure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ch24_differential_expression import load, to_cpm  # noqa: E402

BRCA1_MOUSE = 12189
VIRGIN = ["MCL1-LA", "MCL1-LB"]
LACTATING = ["MCL1-LE", "MCL1-LF"]


def draw() -> plt.Figure:
    counts, _ = load()
    brca1_cpm = to_cpm(counts).loc[BRCA1_MOUSE]
    heights = [brca1_cpm[s] for s in VIRGIN + LACTATING]

    fig, ax = plt.subplots(figsize=(4.6, 2.9))
    ax.bar([0, 1], heights[:2], color="#d62728", label="virgin")
    ax.bar([2, 3], heights[2:], color="#2ca02c", label="pregnant")
    ax.set_xticks([0, 1, 2, 3])
    ax.set_xticklabels(VIRGIN + LACTATING, fontsize=8)
    ax.set_ylim(18, 23.5)
    ax.legend(fontsize=8)
    fig.text(0.5, 0.005, "Lactation halves Brca1 expression in luminal cells.",
             ha="center", fontsize=8.5, style="italic")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    return fig


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "bad_figure.png"
    draw().savefig(out, dpi=150)
    print(f"wrote {out}")
