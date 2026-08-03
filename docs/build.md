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
the only engine that provides both.

## Tagging silently disables titlesec and caption

This is the one thing worth reading before you touch `tex/preamble.tex`.

`\DocumentMetadata{tagging=on}` replaces LaTeX's sectioning commands and its
`\@makecaption` with template-based versions. Packages that work by patching
the originals therefore stop working, and they do not stop loudly:

* `titlesec` writes `Non standard sectioning command \section detected. Using
  default spacing and no format.` into the log and then does nothing. Every
  `\titleformat` in this preamble was dead for the entire first draft, so the
  chapter openers printed stock `book.cls` while the file described a design
  nobody had ever seen on paper.
* `\captionsetup` is discarded the same way, which printed every caption
  centred, at body size, in the roman, under a flush-left ragged-right column.

Both are now done the supported way. Headings are `\DeclareInstance{heading}`
and `\DeclareInstance{headformat}`; captions override the `caption/label`
socket and redefine `\@makecaption` inside `begindocument/end`, which is after
the tagging code's own hook rather than before it.

Two traps inside that fix, both of which cost a build:

* `number-title-sep` is a bare dimension. Passing `{\par\vskip 12pt}` gives
  `Missing number, treated as zero`.
* `\par` closes a tagged paragraph by itself. Emitting `para/end` as well
  double-closes it, and `tagpdf` rejects the whole document with `The number of
  automatic begin and end text para hooks differ`.

The same class of failure applies to colour. `\color{nlrink}` in a preamble
does not survive `\begin{document}`, which issues `\normalcolor`; the book
printed at pure `#000000` until `\normalcolor` itself was redefined.

## The web edition uses system fonts on purpose

The SCSS names Charis and Inconsolata and self-hosts neither. A reader who does
not have them installed gets the fallback stack: Charter or Georgia, and the
system monospace.

That is deliberate. Self-hosting as woff2 would add roughly a megabyte to every
first page load, and this book is written for somebody on a school Chromebook or
paying for data by the gigabyte. Chapter 1 promises that every download states
its size, and quietly spending that on typography would break the promise before
the reader reached Chapter 2.

The PDF carries the full typographic system and is the artifact where the
typography matters. The website is the searchable, screen-readable edition, and
it is fast.

The one thing the fallback does have to preserve is the monospace distinction
between 0/O and 1/l/I, since a reader may type code out of the web edition.
`ui-monospace` resolves to SF Mono, Cascadia Mono or DejaVu Sans Mono depending
on platform, and all three distinguish those characters.

## Figures are styled by a file, not by the chapters

`matplotlibrc` at the project root sets the figure typeface, the spine and tick
weights and the default size. Matplotlib reads it from the working directory and
`_quarto.yml` sets `execute-dir: project`, so it applies to every figure without
a line of styling in any chapter. That matters because three of the four figure
blocks in Chapter 21 are echoed to the reader, and their code has to stay the
plain matplotlib somebody would actually write.

It is deliberately typographic only. Nothing in it changes a colour that carries
data, a scale or a marker, so a reader running the same code on a default
install gets a figure that differs in typeface and frame and in nothing that
would change what they conclude.

One operational note: matplotlib caches the list of installed fonts, and a cache
written before the book's faces were installed still says they do not exist.
`tools/build.sh` deletes that cache on every run, because the alternative is
every figure silently falling back to DejaVu Sans.

## The checks

Ten of them, all wired into CI and into `tools/release_check.sh`.

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
| `check_figures.py` | Every figure has alt text and a caption |
| `check_pages.py` | Every chapter lands within its page budget |
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
