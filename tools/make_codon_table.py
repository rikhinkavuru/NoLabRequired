#!/usr/bin/env python
"""Write the standard genetic code out as a data file the book can ship.

Taken from Biopython's copy of NCBI translation table 1 rather than typed out,
because a codon table typed from memory is 64 chances to be wrong and no reader
would ever catch it.

    .venv/bin/python tools/make_codon_table.py
"""
from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

from Bio.Data import CodonTable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "codon_table_standard.tsv"

AMINO_ACID_NAMES = {
    "A": "Alanine", "R": "Arginine", "N": "Asparagine", "D": "Aspartic acid",
    "C": "Cysteine", "E": "Glutamic acid", "Q": "Glutamine", "G": "Glycine",
    "H": "Histidine", "I": "Isoleucine", "L": "Leucine", "K": "Lysine",
    "M": "Methionine", "F": "Phenylalanine", "P": "Proline", "S": "Serine",
    "T": "Threonine", "W": "Tryptophan", "Y": "Tyrosine", "V": "Valine",
    "*": "stop",
}


def main() -> int:
    table = CodonTable.unambiguous_dna_by_id[1]
    mapping: dict[str, str] = dict(table.forward_table)
    for stop in table.stop_codons:
        mapping[stop] = "*"

    codons = ["".join(c) for c in product("TCAG", repeat=3)]
    missing = [c for c in codons if c not in mapping]
    if missing:
        raise SystemExit(f"table is incomplete, missing {missing}")
    if len(mapping) != 64:
        raise SystemExit(f"expected 64 codons, got {len(mapping)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as fh:
        fh.write("codon\tamino_acid\tname\tis_start\n")
        for codon in codons:
            aa = mapping[codon]
            fh.write(
                f"{codon}\t{aa}\t{AMINO_ACID_NAMES[aa]}\t"
                f"{'yes' if codon in table.start_codons else 'no'}\n"
            )

    counts: dict[str, int] = {}
    for aa in mapping.values():
        counts[aa] = counts.get(aa, 0) + 1

    common = dict(
        source_url="https://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi",
        method="Biopython Bio.Data.CodonTable, NCBI translation table 1 (Standard)",
    )
    facts.record("genetic_code.n_codons", len(mapping), **common)
    facts.record("genetic_code.n_stop_codons", len(table.stop_codons), **common)
    facts.record("genetic_code.stop_codons", sorted(table.stop_codons), **common)
    facts.record("genetic_code.start_codons", sorted(table.start_codons), **common,
                 note="NCBI table 1 lists more than one start codon; ATG is the usual one")
    facts.record("genetic_code.n_amino_acids", len([a for a in counts if a != "*"]), **common)
    facts.record("genetic_code.codons_per_amino_acid", counts, **common,
                 note="how many codons map to each amino acid; the spread is what redundancy means")
    facts.record("genetic_code.max_codons_for_one_amino_acid",
                 max(v for k, v in counts.items() if k != "*"), **common)

    print(f"wrote {OUT.relative_to(ROOT)}: {len(mapping)} codons, "
          f"{len(table.stop_codons)} stops, {len(counts) - 1} amino acids")
    print("start codons:", sorted(table.start_codons))
    print("stop codons:", sorted(table.stop_codons))
    spread = sorted(((v, k) for k, v in counts.items() if k != "*"), reverse=True)
    print("most redundant:", spread[:3], " least:", spread[-3:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
