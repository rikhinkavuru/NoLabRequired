# How this book is built

The source is Quarto markdown. One source produces two editions: a PDF typeset
with LuaLaTeX, and a website. Both come out of `tools/build.sh`.

```bash
bash tools/setup_toolchain.sh   # once: Quarto, TinyTeX, the Python env, the fonts
bash tools/build.sh all         # PDF and site
bash tools/release_check.sh     # everything that must be true before shipping
```

Nothing needs administrator rights. The toolchain installs under your home
directory.

## Why LuaLaTeX and not XeLaTeX

The spec asks for a tagged PDF. LaTeX's tagging support runs on pdfTeX and
LuaTeX and not on XeTeX, and the book also needs OpenType fonts, so LuaLaTeX is
the only engine that provides both. The cost is compile time: a full build of
30 chapters takes several minutes in the LaTeX stage alone, because every
component is a `tcolorbox` and margin material is redistributed page by page.

## Deviations from the typography specification

Two, both deliberate, both because the specified behavior could not be made
correct rather than because it was inconvenient.

### Margins do not mirror

Spec B1 gives an inner margin of 0.75 in and an outer of 1.25 in, which implies
the page mirrors. This build uses `geometry`'s `asymmetric` option instead: the
narrow margin is on the left and the side column on the right, on every page.

A mirrored layout has to decide which direction a full-width element breaks out
of the main column, and that decision depends on which page the element will
land on. LaTeX builds boxes before it knows that, so the answer has to be read
back from the previous compilation pass. It is wrong whenever pagination
shifts, and it fails silently, by pushing text off the trim edge. On a book with
hundreds of full-width components that is not a risk worth carrying for a
symmetry no reader of a digital-first PDF will see.

The alternating running heads are kept, because `fancyhdr` resolves page parity
at shipout, where it is always correct.

### Margin notes use `\marginpar`

The `marginnote` package chooses its side from `\if@twoside` and the page number
directly, ignoring `\@mparswitch`, so it lands in the left margin on even pages
whatever you tell it. `\marginpar` honors `\@mparswitchfalse` and is
deterministic. The cost is that `\marginpar` is illegal inside a box, so every
boxed component rebinds the margin commands to inline fallbacks. The authoring
rule that follows: margin definitions live in body prose, not inside callouts.

`marginfix` is loaded on top, because LaTeX only ever pushes a colliding margin
note downward, and a definition declared near the foot of a page otherwise runs
off the bottom of the paper.

## The checks

Nine of them, all wired into CI and into `tools/release_check.sh`.

| Check | What it proves |
|---|---|
| `check_prose.py` | The voice rules hold. Em dashes are a hard fail. |
| `check_content.py` | Code width, curly quotes in code, chapter structure, glossary coverage, observable checkpoints, unregistered numbers |
| `check_crossrefs.py` | Every "Chapter N" points at a chapter that exists |
| `check_sequences.py` | Every literal DNA sequence appears in a bundled file |
| `check_errors.py` | Every quoted error message is what Python really says |
| `check_data_refs.py` | Every file the book tells a reader to open exists |
| `verify_translation.py` | The coding sequence really does translate to the deposited protein |
| `check_layout.py` | Glyph positions in the rendered PDF match the typography spec, and the delivery spec holds |
| `check_links.py` | Every external address resolves |

`check_layout.py` is the unusual one. It opens the finished PDF, reads where the
glyphs actually landed, and measures them against the specification. Font sizes
are recovered from glyph advance widths rather than from the content stream,
because LuaTeX rescales fonts on embedding and the `Tf` operand is not the point
size.

## Regenerating the data

Everything in `data/` is produced by a script and every script records what it
fetched, from where, and when, into `research/facts.jsonl`.

```bash
.venv/bin/python tools/fetch_facts.py all       # gene, protein, structure records
.venv/bin/python tools/fetch_sequences.py       # the six orthologs, the messy FASTA
.venv/bin/python tools/fetch_datasets.py        # GSE60450, with its labels re-derived
.venv/bin/python tools/fetch_blast.py           # the BLAST searches, validated
.venv/bin/python tools/fetch_alignment.py       # Clustal Omega, the trees
.venv/bin/python tools/make_codon_table.py      # NCBI translation table 1
```

`fetch_datasets.py` refuses to write if marker-gene expression disagrees with
the recorded sample labels. `fetch_blast.py` refuses to store a search whose
database statistics say it never ran, because NCBI reports a failed search as a
clean negative result.
