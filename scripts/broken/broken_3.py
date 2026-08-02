# Exercise 16.1, script 3 of 5.
# It is supposed to work out how many complete codons are in a sequence,
# reading the length off the line the file itself reports.
# Run it, read what comes back, write down the error class, then fix it.

reported_length = "39"          # read from a report file, as text
sequence = "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAAT"

leftover = reported_length % 3

print("complete codons:", reported_length // 3)
print("bases left over:", leftover)
