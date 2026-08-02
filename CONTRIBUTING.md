# Contributing

The most valuable thing you can send is a correction.

## Reporting an error

Open an issue. Quote the page and the sentence. If it's a factual error, say
what the right answer is and where you checked it.

Reports that a described web page no longer looks the way the book says it does
are especially welcome. That's the failure this book is most exposed to, and
readers will hit it before the author does.

## Sending a fix

Fork, edit, open a pull request. Run the checks first:

```bash
bash tools/setup_toolchain.sh    # once
bash tools/release_check.sh      # everything
```

A change that breaks any of them will not merge. The checks are fast except the
build, and the three prose and content ones run in seconds without LaTeX.

## The rules the text follows

They're enforced, not aspirational. `tools/check_prose.py` fails the build on
each of these:

- No em dashes.
- US spelling.
- Contractions in explanatory prose.
- No number that isn't in `research/facts.jsonl`, shown as arithmetic on the
  page, or declared with an `<!-- nlr-allow: N -->` comment.
- No banned vocabulary: delve, leverage, crucial, seamless, robust, realm,
  landscape, foster, harness, unlock, meticulous, simply, easily, obviously.

Every chapter carries a checkpoint whose bullets start with an observable verb.
Every exercise carries a goal, an artifact, and a way to check the answer.

## Adding a fact

Never type a number in from memory. Add it to the registry instead:

```python
import sys; sys.path.insert(0, "tools")
import facts
facts.record("brca1.human.gene_id", "672",
             source_url="https://www.ncbi.nlm.nih.gov/gene/672",
             method="NCBI E-utilities esummary db=gene",
             note="anything a reader would need to judge the number")
```

`tools/check_content.py` will then let the chapter state it, and the dataset
index at the back of the book picks it up automatically.

## What the checks cover

| Check | What it proves |
|---|---|
| `check_prose.py` | The voice rules hold |
| `check_content.py` | Code width, chapter structure, glossary coverage, unregistered numbers |
| `check_crossrefs.py` | Every "Chapter N" points at a chapter that exists |
| `check_sequences.py` | Every literal DNA sequence appears in a bundled file |
| `check_errors.py` | Every quoted error message is what Python really says |
| `check_data_refs.py` | Every file the book tells a reader to open exists |
| `check_figures.py` | Every figure carries alt text |
| `verify_translation.py` | The coding sequence really translates to the deposited protein |
| `check_layout.py` | Glyph positions in the built PDF match the typography spec |
| `check_links.py` | Every external address resolves |

Contributors are named in the changelog.
