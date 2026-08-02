# Exercise 16.1, script 1 of 5.
# It is supposed to report the GC content of a sequence.
# Run it, read what comes back, write down the error class, then fix it.

sequence = "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAAT"

g_count = sequence.count("G")
c_count = sequence.count("C")

gc_fraction = (g_count + c_count / len(sequence)

print("GC content:", round(gc_fraction, 4))
