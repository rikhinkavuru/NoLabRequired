#!/usr/bin/env python
"""Assemble the datasets the book ships with, and prove their labels.

The spine dataset is GSE60450: mouse mammary gland, luminal and basal cell
populations, across virgin / pregnant / lactating. It was chosen because it is
small (513 KB gzipped), it is raw counts rather than someone else's
normalisation, and because it carries a genuine, published trap.

The trap: the column order of the count matrix does not match the order of the
GSM accessions on the GEO series page. Columns run basal-then-luminal;
accessions run luminal-then-basal. A reader who joins them positionally gets
every sample's cell type backwards, and every downstream step still runs, still
plots, and is silently wrong. That is the exact failure this book is built to
teach against, and it did not have to be manufactured.

This script does not take the mapping on trust. It re-derives cell type and
developmental stage from marker-gene expression on every run, and refuses to
write the metadata file if the derivation disagrees with what is recorded here.

    .venv/bin/python tools/fetch_datasets.py
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import facts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

GSE = "GSE60450"
COUNTS_URL = (
    "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE60nnn/GSE60450/suppl/"
    "GSE60450_Lactation-GenewiseCounts.txt.gz"
)

# Entrez IDs resolved from NCBI Gene, not from memory. Verified by
# tools/fetch_facts.py-style lookup on 2026-08-02.
BASAL_MARKERS = {"Krt5": 110308, "Krt14": 16664, "Acta2": 11475, "Trp63": 22061}
LUMINAL_MARKERS = {"Krt8": 16691, "Krt18": 16668, "Elf5": 13711}
# Wap alone, not Wap plus Csn2. Beta-casein is abundant enough in the luminal
# compartment that the small luminal carryover in a basal sort swamps the
# stage signal there and scrambles the ranking; whey acidic protein ramps
# monotonically from virgin to pregnant to lactating in both compartments.
# Csn2 is kept below as an independent cross-check, not as the discriminator.
STAGE_MARKER = {"Wap": 22373}
STAGE_CROSSCHECK = {"Csn2": 12991}

# What the columns really are, to be re-proved from the data below.
EXPECTED = {
    "MCL1-DG": ("basal", "virgin", "GSM1480297"),
    "MCL1-DH": ("basal", "virgin", "GSM1480298"),
    "MCL1-DI": ("basal", "pregnant", "GSM1480299"),
    "MCL1-DJ": ("basal", "pregnant", "GSM1480300"),
    "MCL1-DK": ("basal", "lactating", "GSM1480301"),
    "MCL1-DL": ("basal", "lactating", "GSM1480302"),
    "MCL1-LA": ("luminal", "virgin", "GSM1480291"),
    "MCL1-LB": ("luminal", "virgin", "GSM1480292"),
    "MCL1-LC": ("luminal", "pregnant", "GSM1480293"),
    "MCL1-LD": ("luminal", "pregnant", "GSM1480294"),
    "MCL1-LE": ("luminal", "lactating", "GSM1480295"),
    "MCL1-LF": ("luminal", "lactating", "GSM1480296"),
}


def load_counts() -> tuple[pd.DataFrame, pd.Series, bytes]:
    raw, url = facts.fetch(COUNTS_URL, binary=True)
    text = gzip.decompress(raw).decode()
    df = pd.read_csv(io.StringIO(text), sep="\t", index_col=0)
    length = df.pop("Length")
    df.columns = [c.split("_")[0] for c in df.columns]
    return df, length, raw


def derive_labels(counts: pd.DataFrame) -> dict[str, tuple[str, str]]:
    """Recover cell type and developmental stage from marker expression alone."""
    cpm = counts / counts.sum() * 1e6

    def score(markers: dict[str, int]) -> pd.Series:
        present = [g for g in markers.values() if g in cpm.index]
        return cpm.loc[present].mean()

    basal, luminal = score(BASAL_MARKERS), score(LUMINAL_MARKERS)
    stage_score = score(STAGE_MARKER)
    crosscheck = score(STAGE_CROSSCHECK)

    out: dict[str, str] = {}
    for col in counts.columns:
        out[col] = "basal" if basal[col] > luminal[col] else "luminal"

    # Stage is ordinal within a cell type, so ranking the six samples of one
    # cell type by Wap recovers the three stages two at a time.
    final: dict[str, tuple[str, str]] = {}
    for cell in ("basal", "luminal"):
        cols = [c for c in counts.columns if out[c] == cell]
        ranked = sorted(cols, key=lambda c: stage_score[c])
        for stage, pair in zip(
            ("virgin", "pregnant", "lactating"),
            (ranked[0:2], ranked[2:4], ranked[4:6]),
        ):
            for c in pair:
                final[c] = (cell, stage)
        # Independent confirmation: casein must also be lowest in the pair the
        # Wap ranking called virgin and highest in the pair it called lactating.
        lo = min(crosscheck[c] for c in ranked[0:2])
        hi = max(crosscheck[c] for c in ranked[4:6])
        if not lo < hi:
            raise SystemExit(f"{cell}: Csn2 cross-check contradicts the Wap ranking")
    return final


def main() -> int:
    counts, length, raw = load_counts()
    derived = derive_labels(counts)

    mismatches = [
        (col, derived[col], EXPECTED[col][:2])
        for col in counts.columns
        if derived[col] != EXPECTED[col][:2]
    ]
    if mismatches:
        print("REFUSING TO WRITE: marker-gene derivation disagrees with the recorded mapping")
        for col, got, want in mismatches:
            print(f"  {col}: derived {got}, recorded {want}")
        return 1
    print(f"marker-gene derivation reproduces all {len(counts.columns)} sample labels")

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "GSE60450_counts.tsv.gz").write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()

    meta = pd.DataFrame(
        [
            {
                "sample": col,
                "gsm": EXPECTED[col][2],
                "cell_type": EXPECTED[col][0],
                "stage": EXPECTED[col][1],
                "column_position": i + 1,
                "gsm_position": int(EXPECTED[col][2][3:]) - 1480290,
            }
            for i, col in enumerate(counts.columns)
        ]
    )
    meta.to_csv(DATA / "GSE60450_samples.csv", index=False)
    print(meta.to_string(index=False))

    naive_wrong = sum(
        1
        for i, col in enumerate(counts.columns)
        if EXPECTED[col][0] != EXPECTED[sorted(EXPECTED, key=lambda c: EXPECTED[c][2])[i]][0]
    )

    common = dict(
        source_url=f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={GSE}",
        method="GEO FTP supplementary file + marker-gene label derivation",
    )
    facts.record("gse60450.accession", GSE, **common)
    facts.record("gse60450.n_samples", int(counts.shape[1]), **common)
    facts.record("gse60450.n_genes_raw", int(counts.shape[0]), **common)
    facts.record("gse60450.organism", "Mus musculus", **common)
    facts.record("gse60450.id_type", "NCBI Entrez Gene ID", **common)
    facts.record("gse60450.counts_sha256", digest, **common)
    facts.record("gse60450.counts_bytes", len(raw), unit="bytes", **common)
    facts.record("gse60450.pubmed_id", "25730472", **common)
    facts.record(
        "gse60450.column_order_trap",
        f"{naive_wrong} of {counts.shape[1]} samples get the wrong cell type if the "
        "count-matrix columns are joined positionally to the GSM accession order",
        note="count matrix runs basal-then-luminal; GEO accessions run luminal-then-basal",
        **common,
    )
    facts.record(
        "gse60450.total_library_sizes",
        {c: int(v) for c, v in counts.sum().items()},
        **common,
    )
    print(f"\nwrote data/GSE60450_counts.tsv.gz ({len(raw):,} bytes, sha256 {digest[:16]}...)")
    print(f"positional join would mislabel {naive_wrong}/{counts.shape[1]} samples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
