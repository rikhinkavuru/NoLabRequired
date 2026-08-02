# Exercise 16.1, script 5 of 5.
# It is supposed to translate a short sequence using a small codon table.
# Run it, read what comes back, write down the error class, then fix it.

codon_table = {
    "ATG": "M", "GAT": "D", "TTA": "L", "TCT": "S",
    "GCT": "A", "CGC": "R", "GTT": "V", "GAA": "E",
}

sequence = "ATGGATTTATCTGCTCTTCGCGTTGAA"
codons = [sequence[i:i + 3] for i in range(0, len(sequence), 3)]

protein = ""
for codon in codons:
    protein = protein + codon_table[codon]

print("protein:", protein)
