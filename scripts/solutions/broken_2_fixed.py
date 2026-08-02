# Exercise 16.1, script 2: NameError.
#
# The message was: NameError: name 'sequnce' is not defined.
# It means Python reached a name it had never been given a value for. The
# dictionary was built as `sequences` and used as `sequnce`.
#
# Python offered the answer itself: "Did you mean: 'sequences'?". Read the whole
# last line before you start looking at your code.

# The first 51 bases of each coding sequence, taken from NM_007294.4 and
# NM_009764.3. Both are real.
sequences = {
    "BRCA1_human": "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAATGTCATTAATGCT",
    "Brca1_mouse": "ATGGATTTATCTGCCGTCCAAATTCAAGAAGTACAAAATGTCCTTCATGCT",
}

for name in sequences:
    print(name, len(sequences[name]))
