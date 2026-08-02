#!/usr/bin/env python
"""Collect every term the book marks up, with the chapter that first defines it.

This produces a seed, not the glossary. A glossary assembled by a script reads
like one: the margin definitions are deliberately terse because they have to
fit a 1.65 inch column, and a glossary entry has room to be read cold by
somebody who has not got the surrounding paragraph. The seed is what a writer
expands.

    .venv/bin/python tools/make_glossary_seed.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "research" / "glossary_seed.json"


def main() -> int:
    entries: dict[str, dict] = {}
    for path in sorted((ROOT / "chapters").glob("ch[0-9]*.qmd")):
        if "smoke" in path.name:
            continue
        chapter = int(re.match(r"ch(\d+)", path.name).group(1))
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r'\[([^\]]+)\]\{\.term(?:\s+def="([^"]*)")?[^}]*\}', text):
            term = m.group(1).strip()
            definition = re.sub(r"\s+", " ", (m.group(2) or "").strip())
            key = term.lower()
            if key in entries:
                entries[key]["also_in"].append(chapter)
                continue
            entries[key] = {
                "term": term,
                "margin_definition": definition,
                "first_chapter": chapter,
                "also_in": [],
            }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        [entries[k] for k in sorted(entries)], indent=2, ensure_ascii=False) + "\n")

    print(f"{len(entries)} terms across {len({e['first_chapter'] for e in entries.values()})} chapters")
    missing = [e["term"] for e in entries.values() if not e["margin_definition"]]
    if missing:
        print(f"\n{len(missing)} marked up with no definition attached:")
        for t in missing:
            print(f"  {t}")
    dupes = [(e["term"], e["first_chapter"], e["also_in"]) for e in entries.values() if e["also_in"]]
    if dupes:
        print(f"\n{len(dupes)} term(s) marked up in more than one chapter "
              "(mark a term once, at first use):")
        for term, first, also in dupes:
            print(f"  {term}: first in {first}, again in {also}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
