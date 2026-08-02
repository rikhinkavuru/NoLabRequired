# Exercise 16.1, script 1: SyntaxError.
#
# The message was: SyntaxError: '(' was never closed, and it pointed at line 10.
# A SyntaxError means Python could not finish reading your instruction, so it
# never ran any of the file. Note that the line it names is where the bracket
# was OPENED, not where you noticed the problem.
#
# There were two brackets open and only one closed. The fix also happens to
# change the answer, because without the closing bracket in the right place the
# division would have run before the addition.

sequence = "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAAT"

g_count = sequence.count("G")
c_count = sequence.count("C")

gc_fraction = (g_count + c_count) / len(sequence)

print("GC content:", round(gc_fraction, 4))
