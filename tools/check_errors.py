#!/usr/bin/env python
"""Verify that every error message the book quotes is one Python really produces.

Chapter 16 asks the reader to pattern-match the text on their own screen
against the text on the page. That only works if the page is exact. Error
wording changes between Python versions, and a message that was right in 3.10
can be wrong in 3.14, so this runs each one and compares.

    .venv/bin/python tools/check_errors.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Each case is a snippet that must produce the given final line, verbatim.
CASES: list[tuple[str, str, str]] = [
    ("SyntaxError", "x = (1 + 2\nprint(x)\n",
     "SyntaxError: '(' was never closed"),
    ("IndentationError", "for i in range(3):\nprint(i)\n",
     "IndentationError: expected an indented block after 'for' statement on line 1"),
    ("NameError", "sequences = {'a': 'ATG'}\nprint(sequnce['a'])\n",
     "NameError: name 'sequnce' is not defined. Did you mean: 'sequences'?"),
    ("TypeError concat", "print('length: ' + 39)\n",
     'TypeError: can only concatenate str (not "int") to str'),
    ("TypeError format", "print('39' % 3)\n",
     "TypeError: not all arguments converted during string formatting"),
    ("IndexError", "codons = ['ATG', 'GAT']\nprint(codons[2])\n",
     "IndexError: list index out of range"),
    ("KeyError", "d = {'Brca1_human': 1}\nprint(d['BRCA1'])\n",
     "KeyError: 'BRCA1'"),
    ("FileNotFoundError", "open('counts.tsv')\n",
     "FileNotFoundError: [Errno 2] No such file or directory: 'counts.tsv'"),
]


def last_line(stderr: str) -> str:
    lines = [l for l in stderr.strip().splitlines() if l.strip()]
    return lines[-1] if lines else "(no error raised)"


def main() -> int:
    book = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted((ROOT / "chapters").glob("ch[0-9]*.qmd"))
        if "smoke" not in p.name
    )

    failed = 0
    print(f"\nPython {sys.version.split()[0]}\n")
    for name, snippet, expected in CASES:
        result = subprocess.run(
            [sys.executable, "-c", snippet], capture_output=True, text=True, cwd="/"
        )
        actual = last_line(result.stderr)
        produced = actual == expected
        quoted = expected in book
        ok = produced and quoted
        if not ok:
            failed += 1
        note = ""
        if not produced:
            note = f"interpreter said: {actual}"
        elif not quoted:
            note = "not quoted anywhere in the book"
        print(f"  [{'PASS' if ok else 'FAIL'}] {name.ljust(20)} {note}")

    print(f"\n{len(CASES) - failed}/{len(CASES)} error messages verified verbatim\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
