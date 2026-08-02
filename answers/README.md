# Worked answers

This folder holds the worked answer to every exercise in *No Lab Required*. One
file per chapter that has exercises, named after the chapter: `ch04.md`,
`ch05.md`, and so on down to `ch30.md`. Chapter 3 promised these, and here they
are.

There are 39 exercises across 26 chapters.

## What's in each answer

Four things, in this order, every time.

1. **The goal**, restated in one line, so you can find the exercise you want
   without opening the book.
2. **The answer**, with actual values in it. Where an exercise genuinely has no
   single answer, because it asks about your question or your repository, the
   file gives one worked example and says out loud that it's an example.
3. **Why that's the answer.** Short. The reasoning is the part that transfers to
   the next exercise.
4. **The most common wrong answer, and what produces it.** This is the field
   worth the most and it's in every entry.

Where an exercise wants code, the code in the answer file has been run against
the files in `data/` and the printed values are what it printed.

## Looking before you attempt

You're allowed to read the answer first.

That's the whole position. Nobody is checking, nothing is being graded, and
there's no version of this book that finds out. If you're stuck at 10pm on a
Wednesday with an hour left, and the choice is between reading the answer and
closing the laptop, read the answer. An evening where you understood somebody
else's solution beats an evening you abandoned.

What's true, and worth knowing rather than being lectured about, is that the
answer is the cheap half. The expensive half is the twenty minutes where your
number disagreed with the check box and you found out why. That's the part that
changes what you can do next week. If you read an answer and it made immediate
sense, close the file, delete what you wrote, and do the exercise. You'll find
out in four minutes whether it really made sense.

The exercises that reward attempting first are the predict-then-run ones:
11.1, 12.2, 18.2, 19.2, 24.2 and 27.2. Each one asks you to write a prediction
down before you run anything, and reading the answer first removes the only
thing those exercises measure. Every other exercise survives being read.

## Where else the answers live

`answers/answer-sheet-template.md` is the blank sheet: every exercise in order,
with the time the book budgets for it and a space to write in.

Chapter 16's five broken scripts have their fixed versions in
`scripts/solutions/`, one file per script, each with the diagnosis written into
its header comment. `answers/ch16.md` points at those rather than repeating
them, and adds the diagnosis table the exercise asks for.

Chapter 24's whole pipeline runs end to end in
`scripts/ch24_differential_expression.py`, which is the reference implementation
for every number in Part 4.

## If an answer here disagrees with your run

Check the version and the date before you check your code. Sequence databases
grow, records get corrected, and a version suffix goes up when somebody fixes a
base. The database numbers in these files were read on 2 August 2026 and they
sit in `research/facts.jsonl` with the address each one came from. The computed
numbers come out of the files in `data/`, which don't move, so a disagreement
there is a real disagreement and worth chasing.
