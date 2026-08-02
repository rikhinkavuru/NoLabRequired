# Exercise 16.1, script 3: TypeError.
#
# The message was: TypeError: not all arguments converted during string
# formatting, pointing at `reported_length % 3`.
#
# That wording is confusing until you know why it happens. `reported_length` was
# still text, and % between a string and a number is not remainder, it is
# old-style string formatting. Python was not refusing to divide. It was trying
# to format "39" using 3 as the value, and complaining that it ran out of
# placeholders.
#
# The fix is to turn the text into a number as soon as it arrives. Anything read
# from a file is text until you convert it, every time, without exception.

reported_length = "39"          # read from a report file, as text
sequence = "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAAT"

length = int(reported_length)

# Worth checking that the number the file claims matches the sequence you have.
if length != len(sequence):
    print("warning: the file says", length, "but the sequence is", len(sequence))

print("complete codons:", length // 3)
print("bases left over:", length % 3)
