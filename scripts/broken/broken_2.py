# Exercise 16.1, script 2 of 5.
# It is supposed to print the length of each sequence.
# Run it, read what comes back, write down the error class, then fix it.

# The first 51 bases of each coding sequence, taken from NM_007294.4 and
# NM_009764.3. Both are real.
sequences = {
    "BRCA1_human": "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAATGTCATTAATGCT",
    "Brca1_mouse": "ATGGATTTATCTGCCGTCCAAATTCAAGAAGTACAAAATGTCCTTCATGCT",
}

for name in sequences:
    print(name, len(sequnce[name]))
