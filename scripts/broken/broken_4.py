# Exercise 16.1, script 4 of 5.
# It is supposed to print the last codon of the sequence.
# Run it, read what comes back, write down the error class, then fix it.

sequence = "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAAT"

codons = [sequence[i:i + 3] for i in range(0, len(sequence), 3)]

print("number of codons:", len(codons))
print("last codon:", codons[len(codons)])
