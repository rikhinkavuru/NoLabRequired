#!/usr/bin/env python
"""Build the alignment and tree that Chapters 18 and 19 are written against.

Coding sequences only. Aligning full mRNAs would drag untranslated regions into
a comparison that spans 350 million years, and those are not conserved, so the
alignment would be noise at both ends for reasons that have nothing to do with
what the chapter is teaching.

The multiple alignment is run on EMBL-EBI's public Clustal Omega service, which
is the same route a reader with only a browser would take.

    .venv/bin/python tools/fetch_alignment.py
"""
from __future__ import annotations

import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEQ = ROOT / "data" / "sequences"
ALN = ROOT / "data" / "alignment"

ACCESSIONS = [
    ("human", "NM_007294.4", "Homo sapiens"),
    ("chimpanzee", "NM_001045493.1", "Pan troglodytes"),
    ("mouse", "NM_009764.3", "Mus musculus"),
    ("dog", "NM_001013416.1", "Canis lupus familiaris"),
    ("chicken", "NM_204169.1", "Gallus gallus"),
    ("frog", "NM_001114491.1", "Xenopus tropicalis"),
]

EBI = "https://www.ebi.ac.uk/Tools/services/rest/clustalo"
UA = {"User-Agent": facts.UA}


def cds_of(accession: str) -> tuple[str, int, int]:
    """Return (coding sequence, start, stop) from the GenBank flatfile."""
    text, _ = facts.efetch("nuccore", accession, rettype="gb", retmode="text")
    sequence = "".join(
        re.findall(r"^\s*\d+\s([acgtn ]+)$", text, re.M)
    ).replace(" ", "").upper()
    m = re.search(r"^     CDS\s+(?:join\()?(\d+)\.\.(?:.*?)(\d+)\)?\s*$", text, re.M)
    if not m:
        raise SystemExit(f"{accession}: could not find a simple CDS range")
    a, b = int(m.group(1)), int(m.group(2))
    return sequence[a - 1 : b], a, b


def submit(fasta: str) -> str:
    data = urllib.parse.urlencode({
        "email": "rikhin@virahacks.com",
        "sequence": fasta,
        "stype": "dna",
        "outfmt": "clustal_num",
    }).encode()
    req = urllib.request.Request(f"{EBI}/run", data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode().strip()


def wait(job: str, timeout_s: int = 1800) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        req = urllib.request.Request(f"{EBI}/status/{job}", headers=UA)
        with urllib.request.urlopen(req, timeout=60) as resp:
            status = resp.read().decode().strip()
        if status == "FINISHED":
            return
        if status in ("ERROR", "FAILURE", "NOT_FOUND"):
            raise RuntimeError(f"{job}: {status}")
        print(f"    {job} {status}")
        time.sleep(15)
    raise TimeoutError(job)


def result(job: str, kind: str) -> str:
    req = urllib.request.Request(f"{EBI}/result/{job}/{kind}", headers=UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode()


def wrap(seq: str, width: int = 60) -> str:
    return "\n".join(seq[i : i + width] for i in range(0, len(seq), width))


def main() -> int:
    ALN.mkdir(parents=True, exist_ok=True)
    records = []
    for tag, accession, organism in ACCESSIONS:
        cds, a, b = cds_of(accession)
        records.append((tag, accession, organism, cds))
        print(f"  {tag:11s} {accession:16s} CDS {a}..{b}  {len(cds):>6,} nt  {len(cds)//3:>5,} codons")
        facts.record(
            f"brca1.cds.{tag}.length_nt", len(cds), unit="bp",
            source_url=f"https://www.ncbi.nlm.nih.gov/nuccore/{accession}",
            method=f"CDS range {a}..{b} extracted from the GenBank flatfile",
            note=organism,
        )

    five = [r for r in records if r[0] != "frog"]
    for name, subset in (("five_species", five), ("with_outgroup", records)):
        fasta = "".join(f">{t}\n{wrap(s)}\n" for t, _, _, s in subset)
        (SEQ / f"brca1_cds_{name}.fasta").write_text(fasta)

        target = ALN / f"brca1_cds_{name}.aln"
        if target.exists() and target.stat().st_size > 0:
            print(f"  {name}: already aligned, skipping")
            continue
        print(f"  {name}: submitting {len(subset)} sequences to Clustal Omega")
        job = submit(fasta)
        print(f"    job {job}")
        wait(job)
        target.write_text(result(job, "aln-clustal_num"))
        (ALN / f"brca1_cds_{name}.phylotree").write_text(result(job, "phylotree"))
        (ALN / f"brca1_cds_{name}.pim").write_text(result(job, "pim"))
        print(f"    wrote {target.name} and its tree")
        time.sleep(3)

    print("\nalignments in data/alignment/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
