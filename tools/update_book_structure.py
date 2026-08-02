#!/usr/bin/env python
"""Rewrite the chapter list in _quarto.yml from the canonical book structure.

The structure below is the whole book. Files that do not exist yet are skipped
with a note, so the book can be built and measured at any point during writing
rather than only at the end.

    .venv/bin/python tools/update_book_structure.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "_quarto.yml"

STRUCTURE: list[tuple[str | None, list[str]]] = [
    (None, [
        "index.qmd",
        "frontmatter/contents.qmd",
        "frontmatter/acknowledgments.qmd",
    ]),
    ("parts/p0-start-here.qmd", [
        "chapters/ch01-who-this-is-for.qmd",
        "chapters/ch02-what-computational-biology-is.qmd",
        "chapters/ch03-how-this-workbook-works.qmd",
        "chapters/ch04-your-one-and-only-setup.qmd",
    ]),
    ("parts/p1-first-analysis.qmd", [
        "chapters/ch05-reading-a-gene.qmd",
        "chapters/ch06-blast.qmd",
        "chapters/ch07-what-results-mean.qmd",
        "chapters/ch08-proteins-without-a-microscope.qmd",
        "chapters/ch09-checkpoint-what-you-just-did.qmd",
    ]),
    ("parts/p2-enough-python.qmd", [
        "chapters/ch10-why-code-at-all.qmd",
        "chapters/ch11-variables-strings-and-dna.qmd",
        "chapters/ch12-loops-and-conditionals.qmd",
        "chapters/ch13-lists-dictionaries-genetic-code.qmd",
        "chapters/ch14-functions.qmd",
        "chapters/ch15-files-and-formats.qmd",
        "chapters/ch16-reading-errors.qmd",
    ]),
    ("parts/p3-real-data.qmd", [
        "chapters/ch17-biopython.qmd",
        "chapters/ch18-sequence-alignment.qmd",
        "chapters/ch19-multiple-alignment-and-trees.qmd",
        "chapters/ch20-tabular-data-with-pandas.qmd",
        "chapters/ch21-figures-that-communicate.qmd",
    ]),
    ("parts/p4-complete-project.qmd", [
        "chapters/ch22-framing-a-question.qmd",
        "chapters/ch23-finding-data.qmd",
        "chapters/ch24-walkthrough-differential-expression.qmd",
        "chapters/ch25-interpreting-results.qmd",
        "chapters/ch26-writing-it-up-and-sharing-it.qmd",
    ]),
    ("parts/p5-where-this-goes.qmd", [
        "chapters/ch27-practicing.qmd",
        "chapters/ch28-getting-in-without-credentials.qmd",
        "chapters/ch29-what-the-field-looks-like.qmd",
        "chapters/ch30-resources.qmd",
    ]),
    ("backmatter/_backmatter.qmd", [
        "backmatter/glossary.qmd",
        "backmatter/error-index.qmd",
        "backmatter/cheat-sheet.qmd",
        "backmatter/dataset-index.qmd",
        "backmatter/about-the-author.qmd",
        "backmatter/changelog.qmd",
    ]),
]


def build_block() -> tuple[str, list[str], list[str]]:
    lines: list[str] = ["  chapters:"]
    present: list[str] = []
    missing: list[str] = []
    for part, chapters in STRUCTURE:
        have = [c for c in chapters if (ROOT / c).exists()]
        missing += [c for c in chapters if not (ROOT / c).exists()]
        if part is None:
            for c in have:
                lines.append(f"    - {c}")
                present.append(c)
            continue
        if not have:
            continue
        if (ROOT / part).exists():
            lines.append(f"    - part: {part}")
        else:
            lines.append(f"    - part: \"{Path(part).stem}\"")
            missing.append(part)
        lines.append("      chapters:")
        for c in have:
            lines.append(f"        - {c}")
            present.append(c)
    return "\n".join(lines) + "\n", present, missing


def main() -> int:
    block, present, missing = build_block()
    text = CONFIG.read_text()
    pattern = re.compile(r"^  chapters:\n(?:^(?:    |      |        ).*\n)*", re.M)
    if not pattern.search(text):
        print("could not find the chapters block in _quarto.yml")
        return 1
    CONFIG.write_text(pattern.sub(block, text, count=1))

    print(f"wired {len(present)} files into _quarto.yml")
    if missing:
        print(f"\nnot written yet ({len(missing)}):")
        for m in missing:
            print(f"  {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
