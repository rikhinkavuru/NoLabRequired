# Exercise 16.1, script 5: KeyError.
#
# The message was: KeyError: 'CTT'.
# A KeyError names the key that was missing, and that name is the whole clue.
# The codon CTT appears in the sequence and is not in the table, because the
# table only ever had eight codons in it and the real genetic code has 64.
#
# This is the most expensive of the five errors, because the same shape of
# mistake in a real analysis is usually a gene identifier that exists in one
# file and not in another. The error is telling you your two inputs disagree.
#
# There are two fixes and they are not equivalent.
#
#   1. Add the missing entry. Correct when the table was genuinely incomplete,
#      which is the case here.
#   2. Use .get(codon, "X") to substitute a placeholder. Correct only when a
#      missing key is expected and meaningful. Reach for this too early and you
#      have converted a loud failure into a silent wrong answer, which is worse.
#
# Chapter 13 builds the full 64-codon table properly.

codon_table = {
    "ATG": "M", "GAT": "D", "TTA": "L", "TCT": "S",
    "GCT": "A", "CTT": "L", "CGC": "R", "GTT": "V", "GAA": "E",
}

sequence = "ATGGATTTATCTGCTCTTCGCGTTGAA"
codons = [sequence[i:i + 3] for i in range(0, len(sequence), 3)]

missing = [c for c in codons if c not in codon_table]
if missing:
    raise SystemExit(f"codon table is missing: {sorted(set(missing))}")

protein = ""
for codon in codons:
    protein = protein + codon_table[codon]

print("protein:", protein)
