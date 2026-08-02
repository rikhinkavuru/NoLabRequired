"""The Part 4 analysis, run end to end on GSE60450.

This is the reference implementation of what Chapters 24 and 25 walk through.
It is deliberately built from tools a reader has already met: pandas, a filter,
a log transform, and a t-test from scipy. It is not what a working analyst
would run, and the book says so: real differential expression uses a
negative-binomial model such as DESeq2 or edgeR, because counts are not normal
and small counts are noisier than large ones in a way a t-test cannot see.

What this version does have is that every step is legible to somebody who has
read Chapters 11 to 21, and that matters more here than an extra decimal place.

    .venv/bin/python scripts/ch24_differential_expression.py
"""
from __future__ import annotations

import gzip
import io
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
COUNTS = ROOT / "data" / "GSE60450_counts.tsv.gz"
SAMPLES = ROOT / "data" / "GSE60450_samples.csv"

BRCA1_MOUSE = 12189
MIN_CPM = 1.0
MIN_SAMPLES = 3


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    text = gzip.decompress(COUNTS.read_bytes()).decode()
    counts = pd.read_csv(io.StringIO(text), sep="\t", index_col=0)
    counts.pop("Length")
    counts.columns = [c.split("_")[0] for c in counts.columns]
    samples = pd.read_csv(SAMPLES).set_index("sample")
    # Join by key, never by position. The whole of Chapter 24 turns on this.
    samples = samples.loc[counts.columns]
    return counts, samples


def to_cpm(counts: pd.DataFrame) -> pd.DataFrame:
    return counts / counts.sum() * 1e6


def filter_low(counts: pd.DataFrame, cpm: pd.DataFrame) -> pd.DataFrame:
    keep = (cpm >= MIN_CPM).sum(axis=1) >= MIN_SAMPLES
    return counts.loc[keep]


def compare(logcpm: pd.DataFrame, group_a: list[str], group_b: list[str],
            name_a: str, name_b: str) -> pd.DataFrame:
    a = logcpm[group_a]
    b = logcpm[group_b]
    t, p = stats.ttest_ind(b, a, axis=1)
    result = pd.DataFrame(
        {
            f"mean_{name_a}": a.mean(axis=1),
            f"mean_{name_b}": b.mean(axis=1),
            "log2_fold_change": b.mean(axis=1) - a.mean(axis=1),
            "t": t,
            "p_value": p,
        },
        index=logcpm.index,
    )
    result["p_adjusted"] = benjamini_hochberg(result["p_value"].values)
    return result.sort_values("p_value")


def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    """Control the false discovery rate. Written out so Chapter 25 can show it.

    A gene whose expression does not vary at all within either group gives the
    t-test nothing to divide by, and scipy returns NaN. Those have to be set
    aside explicitly. Left in, a single NaN propagates backwards through the
    running minimum below and silently destroys every adjusted value in the
    table, which is the kind of failure this book exists to teach against.
    """
    out = np.full(len(p), np.nan)
    usable = ~np.isnan(p)
    q = p[usable]
    n = len(q)
    if n == 0:
        return out
    order = np.argsort(q)
    ranked = q[order] * n / (np.arange(n) + 1)
    # Adjusted values must not decrease as the raw p-value rises.
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adjusted = np.empty(n)
    adjusted[order] = np.clip(ranked, 0, 1)
    out[usable] = adjusted
    return out


def main() -> None:
    counts, samples = load()
    cpm = to_cpm(counts)
    kept = filter_low(counts, cpm)
    logcpm = np.log2(to_cpm(kept) + 1)

    print(f"genes before filtering: {counts.shape[0]:,}")
    print(f"genes after filtering:  {kept.shape[0]:,}")
    print(f"library sizes: {counts.sum().min():,} to {counts.sum().max():,} reads")

    basal = samples.index[samples.cell_type == "basal"].tolist()
    luminal = samples.index[samples.cell_type == "luminal"].tolist()

    print("\n=== basal vs luminal, 6 against 6 ===")
    by_cell = compare(logcpm, basal, luminal, "basal", "luminal")
    report(by_cell)

    bas_virgin = samples.index[(samples.cell_type == "basal") & (samples.stage == "virgin")].tolist()
    bas_lact = samples.index[(samples.cell_type == "basal") & (samples.stage == "lactating")].tolist()

    print("\n=== within basal only: virgin vs lactating, 2 against 2 ===")
    by_stage = compare(logcpm, bas_virgin, bas_lact, "virgin", "lactating")
    report(by_stage)

    print("\n=== Brca1 ===")
    for label, table in (("basal vs luminal", by_cell), ("virgin vs lactating (basal)", by_stage)):
        if BRCA1_MOUSE in table.index:
            row = table.loc[BRCA1_MOUSE]
            rank = int((table["p_value"] < row["p_value"]).sum()) + 1
            print(f"  {label:32s} log2FC={row['log2_fold_change']:+.2f} "
                  f"p={row['p_value']:.3g} p_adj={row['p_adjusted']:.3g} rank={rank}")
        else:
            print(f"  {label:32s} filtered out before testing")


def report(table: pd.DataFrame) -> None:
    p = table["p_value"].dropna()
    sig = (table["p_adjusted"] < 0.05).sum()
    print(f"  genes tested:                     {len(p):,}")
    print(f"  no variance, not testable:        {table['p_value'].isna().sum():,}")
    print(f"  raw p below 0.05:                 {(p < 0.05).sum():,}")
    print(f"  genes with adjusted p below 0.05: {sig:,}")
    # The shape of the p-value distribution is the cheapest diagnostic there is.
    # Under a true null it is flat, so the median sits near 0.5. A median far
    # below that means the test's assumptions are not being met, and with two
    # replicates per group they are not.
    print(f"  median p-value:                   {p.median():.4f}  "
          f"(near 0.5 when the test is behaving)")
    print("  strongest five by p-value:")
    for gene, row in table.head(5).iterrows():
        print(f"    {gene:>10} log2FC={row['log2_fold_change']:+7.2f} "
              f"p={row['p_value']:.2e} p_adj={row['p_adjusted']:.2e}")


if __name__ == "__main__":
    main()
