#!/usr/bin/env python
"""Every file the book tells a reader to open must exist in the repository.

A chapter that says `data/sequences/messy.fasta` and ships no such file wastes
the reader's evening and cannot be recovered from, because they have no way to
tell whether the file is missing or they mistyped it.

    .venv/bin/python tools/check_data_refs.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Paths the book mentions that are not files in this repository.
EXTERNAL = {
    "data/",  # the directory itself, referred to generically
}

PATTERN = re.compile(
    r"`((?:data|scripts|notebooks|answers|backmatter|chapters)/[A-Za-z0-9._/-]+)`"
)


def main() -> int:
    missing: list[tuple[str, int, str]] = []
    seen: set[str] = set()

    targets = (
        sorted((ROOT / "chapters").glob("*.qmd"))
        + sorted((ROOT / "backmatter").glob("*.qmd"))
        + sorted((ROOT / "frontmatter").glob("*.qmd"))
        + sorted((ROOT / "answers").glob("*.md"))
        + [ROOT / "index.qmd", ROOT / "README.md"]
    )
    for path in targets:
        if not path.exists() or "smoke" in path.name:
            continue
        text = path.read_text(encoding="utf-8")
        for m in PATTERN.finditer(text):
            ref = m.group(1)
            if ref in EXTERNAL or ref.endswith("/"):
                continue
            seen.add(ref)
            if not (ROOT / ref).exists():
                line = text[: m.start()].count("\n") + 1
                missing.append((str(path.relative_to(ROOT)), line, ref))

    for where, line, ref in missing:
        print(f"  [FAIL] {where}:{line}  {ref} does not exist")
    print(f"\n{len(seen) - len(missing)}/{len(seen)} referenced files present\n")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
