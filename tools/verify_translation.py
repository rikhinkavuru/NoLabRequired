#!/usr/bin/env python
"""Translate the real BRCA1 coding sequence and check it against the real protein.

This is the end-to-end test for a chain the book leans on in three places: the
coding-range arithmetic in Chapter 5, the codon table built in Chapter 13, and
the claim that a reader can reproduce a deposited protein from a deposited
transcript. If any link in that chain is wrong, this fails.

    .venv/bin/python tools/verify_translation.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Bundled rather than pulled from the scratch directory, so this proof runs on
# a fresh clone with no network. It is the same record Chapter 5 reads and the
# same one Chapter 13's exercise checks a translation against.
GENBANK = ROOT / "data" / "NM_007294.4.gb"
CODONS = ROOT / "data" / "codon_table_standard.tsv"


def load_genbank(path: Path) -> tuple[str, tuple[int, int], str]:
    text = path.read_text()
    sequence = "".join(
        re.findall(r"^\s*\d+\s([acgtn ]+)$", text, re.M)
    ).replace(" ", "").upper()
    cds = re.search(r"^     CDS\s+(\d+)\.\.(\d+)", text, re.M)
    protein = re.sub(r"\s+", "", re.search(r'/translation="([^"]+)"', text, re.S).group(1))
    return sequence, (int(cds.group(1)), int(cds.group(2))), protein


def load_codon_table(path: Path) -> dict[str, str]:
    with open(path) as fh:
        return {row["codon"]: row["amino_acid"] for row in csv.DictReader(fh, delimiter="\t")}


def main() -> int:
    if not GENBANK.exists():
        print(f"missing {GENBANK}")
        return 2
    if not CODONS.exists():
        print(f"missing {CODONS}; run tools/make_codon_table.py first")
        return 2

    sequence, (start, stop), deposited = load_genbank(GENBANK)
    table = load_codon_table(CODONS)

    # The range is 1-based and includes both ends, which is where the off-by-one
    # in Chapter 5 lives.
    coding = sequence[start - 1 : stop]
    codons = [coding[i : i + 3] for i in range(0, len(coding), 3)]
    translated = "".join(table[c] for c in codons)
    protein = translated.rstrip("*")

    checks = [
        ("coding length divisible by 3", len(coding) % 3 == 0, f"{len(coding)} nt"),
        ("last codon is a stop", translated.endswith("*"), f"{codons[-1]} -> {translated[-1]}"),
        ("exactly one stop, at the end", translated.count("*") == 1, f"{translated.count('*')} stop codons"),
        ("length matches the deposited protein", len(protein) == len(deposited),
         f"{len(protein)} vs {len(deposited)}"),
        ("sequence matches the deposited protein", protein == deposited,
         "identical" if protein == deposited else "differs"),
    ]

    failed = 0
    print(f"\nNM_007294.4, CDS {start}..{stop}, {len(codons)} codons\n")
    for name, ok, detail in checks:
        if not ok:
            failed += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {name.ljust(38)} {detail}")

    if protein != deposited:
        for i, (a, b) in enumerate(zip(protein, deposited)):
            if a != b:
                print(f"\n  first difference at residue {i + 1}: got {a}, expected {b}")
                break

    print(f"\n{len(checks) - failed}/{len(checks)} checks passed\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
