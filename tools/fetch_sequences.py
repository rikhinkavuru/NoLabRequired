#!/usr/bin/env python
"""Build the sequence files the book ships with.

Everything here is real sequence pulled from RefSeq. The one file that is
deliberately damaged, data/sequences/messy.fasta, is damaged in ways that are
documented here and that occur in the wild; the underlying sequence is still
real.

    .venv/bin/python tools/fetch_sequences.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEQ = ROOT / "data" / "sequences"

# BRCA1 across five species for the Chapter 19 tree, plus one outgroup for 19.2.
#
# The accessions are pinned rather than searched for, for two reasons. A search
# returns whichever transcript variant NCBI happens to rank first, which drifts
# between runs and would silently change the answer to a published exercise. And
# the human entry has to be the same NM_007294.4 the reader met in Chapter 5;
# calling the same gene by two different accessions across one book is the
# elegant-variation failure the style bible bans.
#
# All six are curated RefSeq records (NM_ prefix), not model predictions (XM_).
# Every one is re-verified against the live record on each run.
SPECIES = [
    ("human", "NM_007294.4", "Homo sapiens"),
    ("chimpanzee", "NM_001045493.1", "Pan troglodytes"),
    ("mouse", "NM_009764.3", "Mus musculus"),
    ("dog", "NM_001013416.1", "Canis lupus familiaris"),
    ("chicken", "NM_204169.1", "Gallus gallus"),
]
# Roughly 350 million years from the mammals, and still a curated brca1.
OUTGROUP = ("frog", "NM_001114491.1", "Xenopus tropicalis")


def verify(accession: str, expect_organism: str) -> tuple[str, str]:
    """Confirm a pinned accession still resolves to the species we expect."""
    text, _ = facts.efetch("nuccore", accession, rettype="gb", retmode="text")
    version = re.search(r"^VERSION\s+(\S+)", text, re.M).group(1)
    organism = re.search(r"^  ORGANISM  (.+)$", text, re.M).group(1).strip()
    if organism != expect_organism:
        raise SystemExit(
            f"{accession} now resolves to {organism!r}, not {expect_organism!r}. "
            "Do not paper over this: check the record and update the pin."
        )
    if version != accession:
        print(f"    note: {accession} has been superseded by {version}")
    return version, organism


def wrap(seq: str, width: int = 60) -> str:
    return "\n".join(seq[i : i + width] for i in range(0, len(seq), width))


def fasta_seq(text: str) -> str:
    return "".join(l.strip() for l in text.splitlines() if not l.startswith(">"))


def main() -> int:
    SEQ.mkdir(parents=True, exist_ok=True)
    records: list[tuple[str, str, str, str]] = []  # tag, organism, accession, seq

    for tag, pinned, expect in SPECIES + [OUTGROUP]:
        accession, real_organism = verify(pinned, expect)
        fa, _ = facts.efetch("nuccore", accession, rettype="fasta", retmode="text")
        seq = fasta_seq(fa)
        records.append((tag, real_organism, accession, seq))
        print(f"  {tag:11s} {accession:16s} {len(seq):>7,} bp  {real_organism}")
        facts.record(
            f"brca1.tree.{tag}.accession", accession,
            source_url=f"https://www.ncbi.nlm.nih.gov/nuccore/{accession}",
            method="NCBI esearch nuccore + efetch rettype=fasta",
            note=real_organism,
        )
        facts.record(
            f"brca1.tree.{tag}.length_nt", len(seq), unit="bp",
            source_url=f"https://www.ncbi.nlm.nih.gov/nuccore/{accession}",
            method="length of the fetched RefSeq mRNA",
        )

    five = [r for r in records if r[0] != OUTGROUP[0]]
    with open(SEQ / "brca1_five_species.fasta", "w") as fh:
        for tag, organism, accession, seq in five:
            fh.write(f">{tag}|{accession} {organism} BRCA1 mRNA\n{wrap(seq)}\n")
    out = [r for r in records if r[0] == OUTGROUP[0]]
    if out:
        tag, organism, accession, seq = out[0]
        with open(SEQ / "brca1_outgroup.fasta", "w") as fh:
            fh.write(f">{tag}|{accession} {organism} brca1 mRNA\n{wrap(seq)}\n")

    # ---- the deliberately messy multi-FASTA for Exercise 15.1 -------------
    # Four defects, all of which occur in files people really send each other:
    #   1. one record wrapped at 60 columns and one on a single long line
    #   2. a blank line inside a record
    #   3. a header containing spaces, so splitting on whitespace loses the ID
    #   4. a trailing asterisk left over from a translation tool
    # None of these is invalid FASTA. All of them break a naive parser.
    if len(records) >= 3:
        a, b, c = records[0], records[1], records[2]
        with open(SEQ / "messy.fasta", "w") as fh:
            fh.write(f">{a[2]} {a[1]} BRCA1 mRNA, wrapped\n{wrap(a[3][:480])}\n")
            fh.write(f">{b[2]} {b[1]} BRCA1 mRNA, one long line\n{b[3][:420]}\n")
            fh.write(f">{c[2]} {c[1]} BRCA1 mRNA, blank line inside\n")
            fh.write(wrap(c[3][:240]) + "\n\n" + wrap(c[3][240:480]) + "\n")
            fh.write(f">{a[2]}_translated leftover stop character\n")
            fh.write(wrap(a[3][:180]) + "*\n")
        text = (SEQ / "messy.fasta").read_text()
        facts.record(
            "messy_fasta.n_records", text.count(">"),
            source_url="data/sequences/messy.fasta",
            method="count of header lines in the generated file",
            note="built by tools/fetch_sequences.py from real RefSeq sequence with four "
                 "documented defects: mixed wrapping, an internal blank line, spaces in "
                 "headers, and a trailing asterisk",
        )
        lengths = {}
        for block in text.split(">")[1:]:
            lines = block.splitlines()
            ident = lines[0].split()[0]
            body = "".join(l for l in lines[1:] if l.strip())
            lengths[ident] = len(body.rstrip("*"))
        facts.record(
            "messy_fasta.record_lengths", lengths,
            source_url="data/sequences/messy.fasta",
            method="sequence length per record, blank lines removed, trailing * stripped",
        )
        print("\n  messy.fasta record lengths:", lengths)

    print(f"\nwrote {len(records)} sequence records to data/sequences/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
