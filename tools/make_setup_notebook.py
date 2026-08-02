#!/usr/bin/env python
"""Generate notebooks/setup.ipynb, the one notebook Chapter 4 asks readers to run.

It has to do three things and nothing else: prove the reader's notebook can run
code, prove it can reach the internet, and print one line they can paste into
Exercise 4.1 so they have evidence it worked. It deliberately installs nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "notebooks" / "setup.ipynb"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


CELLS = [
    md(
        """# No Lab Required: setup check

This is the only setup you will do for this book. It installs nothing.

Run the cells below in order, top to bottom. Use the run button on the left of
each cell, or press Shift and Enter together.

If a cell prints something in red, that is not necessarily a failure. Chapter 4
explains how to tell the difference.
"""
    ),
    md(
        """## 1. Can this notebook run code at all?

The cell below adds two numbers. If it prints `4`, the notebook is working.
"""
    ),
    code("2 + 2"),
    md(
        """## 2. What is actually running this?

A notebook is a text file. The thing that runs your code is a separate program
called a kernel, sitting on a machine somewhere else. This cell asks it what it
is.
"""
    ),
    code(
        """import platform
import sys

print("Python", platform.python_version())
print("running on", platform.system(), platform.machine())
"""
    ),
    md(
        """## 3. Can it reach the internet?

Almost everything in this book fetches data from a public database. This cell
asks NCBI which databases it has. If it prints a list, you are connected.

It downloads well under one kilobyte.
"""
    ),
    code(
        """import json
import urllib.request

url = (
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi"
    "?retmode=json&tool=no-lab-required&email=reader@example.com"
)
with urllib.request.urlopen(url, timeout=30) as response:
    databases = json.load(response)["einforesult"]["dblist"]

print("NCBI is reachable and lists", len(databases), "databases")
print("the ones this book uses:")
for name in ("gene", "nuccore", "protein", "clinvar", "gds"):
    print("  ", name, "present" if name in databases else "MISSING")
"""
    ),
    md(
        """## 4. Are the libraries this book uses already here?

Colab ships with most of what we need. Chapter 17 installs the one library it
does not ship with, and that is the only install in the whole book.
"""
    ),
    code(
        """for name in ("numpy", "pandas", "matplotlib", "scipy"):
    try:
        module = __import__(name)
        print(f"{name:12s} {getattr(module, '__version__', 'present')}")
    except ImportError:
        print(f"{name:12s} NOT INSTALLED")

try:
    import Bio
    print(f"{'biopython':12s} {Bio.__version__}")
except ImportError:
    print(f"{'biopython':12s} not installed yet, which is expected. Chapter 17 installs it.")
"""
    ),
    md(
        """## 5. Your answer to Exercise 4.1

Run this cell and copy the single line it prints into the answer space in
Chapter 4. It is the evidence that your setup works.
"""
    ),
    code(
        """import datetime
import platform
import sys

line = "NLR setup OK | Python {} | {} | {}".format(
    platform.python_version(),
    platform.system(),
    datetime.date.today().isoformat(),
)
print(line)
"""
    ),
    md(
        """## 6. One thing to try before you go

Go back to cell 1, change `2 + 2` to `2 +`, and run it. Read what comes back.

You have just made your first `SyntaxError`, on purpose, at a moment when
nothing was at stake. Change it back and run it again. Chapter 16 is about
reading these properly.
"""
    ),
]

NOTEBOOK = {
    "cells": CELLS,
    "metadata": {
        "colab": {"provenance": [], "toc_visible": True},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(NOTEBOOK, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} with {len(CELLS)} cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
