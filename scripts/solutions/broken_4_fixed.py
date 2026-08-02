# Exercise 16.1, script 4: IndexError.
#
# The message was: IndexError: list index out of range.
# There are 13 codons, so their positions are numbered 0 to 12. Asking for
# position 13 asks for the fourteenth item in a list of thirteen.
#
# This is the off-by-one from Chapter 11 in its most common form: the length of
# a list is always one more than the position of its last item. Either subtract
# one, or use -1, which counts from the end and cannot drift.

sequence = "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAAT"

codons = [sequence[i:i + 3] for i in range(0, len(sequence), 3)]

print("number of codons:", len(codons))
print("last codon:", codons[-1])
