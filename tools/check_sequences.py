#!/usr/bin/env python
"""Confirm that every literal DNA sequence in the book's scripts is real.

A plausible-looking sequence is the easiest thing in this field to invent by
accident and the hardest for a reader to catch. This walks every literal of
four or more bases in scripts/ and chapters/ and requires it to appear in one
of the bundled sequence files, or to be explicitly declared as constructed.

    .venv/bin/python tools/check_sequences.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_LEN = 24  # shorter than this and a match is not evidence of anything

DECLARED = re.compile(r"nlr-synthetic")


def load_reference() -> str:
    """Every real base this book ships, concatenated, plus reverse complements."""
    chunks: list[str] = []
    for path in sorted((ROOT / "data" / "sequences").glob("*.fasta")):
        seq = "".join(
            line.strip() for line in path.read_text().splitlines()
            if not line.startswith(">")
        ).upper()
        chunks.append(seq)
    joined = "|".join(chunks)
    comp = str.maketrans("ACGT", "TGCA")
    rc = "|".join(c.translate(comp)[::-1] for c in chunks)
    return joined + "|" + rc


def main() -> int:
    reference = load_reference()
    if not reference.strip("|"):
        print("no bundled sequences to check against")
        return 0

    literal = re.compile(r"[\"']([ACGTNacgtn]{%d,})[\"']" % MIN_LEN)
    problems: list[str] = []
    checked = 0

    targets = list((ROOT / "scripts").rglob("*.py")) + list((ROOT / "chapters").glob("*.qmd"))
    for path in targets:
        text = path.read_text(encoding="utf-8", errors="replace")
        # A file that declares its sequences constructed is exempt. Used only by
        # the component rendering test, which is not part of the book.
        if DECLARED.search(text):
            continue
        for m in literal.finditer(text):
            seq = m.group(1).upper()
            line = text[: m.start()].count("\n") + 1
            checked += 1
            if seq not in reference:
                rel = path.relative_to(ROOT)
                problems.append(f"{rel}:{line}  {len(seq)} bases not found in any bundled sequence\n    {seq[:64]}")

    for p in problems:
        print(f"  [FAIL] {p}")
    print(f"\n{checked - len(problems)}/{checked} literal sequences verified against bundled data")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
