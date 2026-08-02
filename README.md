# No Lab Required

**A bioinformatics workbook for people with no lab, no degree, and no budget.**

Everything runs in a web browser. Nothing here requires an install, a terminal,
an institutional login, or a paid account.

[Read it online](https://rikhinkavuru.github.io/NoLabRequired/) ·
[Download the PDF](https://github.com/rikhinkavuru/NoLabRequired/releases/latest)

---

## What this is

Thirty chapters and about 240 pages, in six parts. You start by looking up a
gene in a public database, and you finish by publishing a differential
expression analysis you ran yourself on real data.

| Part | Chapters | What happens |
|---|---|---|
| 0 Start here | 1 to 4 | Whether this is for you, and where your code will run |
| 1 Your first real analysis | 5 to 9 | Real work, no code at all |
| 2 Enough Python to be dangerous | 10 to 16 | Python, taught entirely on sequences |
| 3 Working with real data | 17 to 21 | Biopython, alignment, trees, tables, figures |
| 4 A complete project | 22 to 26 | One question, one dataset, one published result |
| 5 Where this goes | 27 to 30 | Practising, and getting taken seriously without a credential |

The book follows one gene and one dataset the whole way. BRCA1 arrives in
Chapter 5 as a database record and comes back in Chapter 24 as a line in the
reader's own results table.

## What is in this repository

```
chapters/     the book, one .qmd file per chapter
parts/        part title pages
backmatter/   glossary, error index, cheat sheet, dataset index
data/         every dataset the book uses, bundled so nothing depends on a download
notebooks/    the setup notebook from Chapter 4
scripts/      the code files the chapters refer to by name
research/     the fact registry, the style bible, the beat sheet
tex/ scss/    the typographic system, for print and for the web
filters/      the pandoc filter that maps one source to both editions
tools/        the build and the tests
```

## How the book keeps itself honest

The hard part of a book like this is not writing it. It is making sure that
nothing in it is quietly wrong, and that it stays that way as databases grow and
websites get redesigned. Four mechanisms do that work.

**A fact registry.** Every externally-sourced number in the book lives in
`research/facts.jsonl` with the URL it came from, the request that produced it,
and the date it was retrieved. `tools/check_content.py` flags any number in the
prose that is not either in the registry, shown as arithmetic on the page, or
explicitly declared. The dataset index at the back of the book is generated from
the same file, so it cannot drift.

**Executed code.** Code that reads bundled data is run at build time and its
printed output is the real output. The book cannot show you a result its own
code does not produce.

**Verified labels.** `tools/fetch_datasets.py` re-derives the sample labels for
the main dataset from marker-gene expression on every run and refuses to write
the metadata file if its derivation disagrees with the recorded mapping. It
caught a real error the first time it ran.

**Three test harnesses.**

```bash
.venv/bin/python tools/check_layout.py _book/bioinformatics-workbook-v1.0.pdf
.venv/bin/python tools/check_prose.py --all --stats
.venv/bin/python tools/check_content.py
```

`check_layout.py` reads glyph positions out of the rendered PDF and measures
them against the typographic specification, so a broken layout fails a test
instead of surprising somebody at print time. `check_prose.py` enforces the
voice rules in `research/STYLE_BIBLE.md`. `check_content.py` covers code width,
curly quotes inside code blocks, chapter structure, glossary coverage, and
unverified numbers.

## Building it

```bash
bash tools/setup_toolchain.sh   # Quarto, TinyTeX, the Python env, the fonts
bash tools/build.sh all         # PDF and website
```

The toolchain installs into your home directory and needs no administrator
rights. Fonts are Source Serif 4, Inter, and JetBrains Mono NL, all
open-licensed.

## Contributing

If you find an error, open an issue. Quote the page and the sentence.

If you fix one, open a pull request. Run the three checks above first;
a change that breaks them will not merge. Contributors are named in the
changelog.

Corrections to the science are the most valuable thing you can send. So is
telling us that a described web page no longer looks the way the book says it
does, because that is the failure mode this book is most exposed to.

## License

The text is licensed
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). The code
in `tools/`, `scripts/`, and `filters/` is MIT.

Data bundled in `data/` comes from public repositories and remains subject to
the terms of the archives that host it; each file's source, accession, and
retrieval date is in the dataset index at the back of the book.
