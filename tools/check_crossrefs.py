#!/usr/bin/env python
"""Check every cross-reference the book makes to another chapter.

The chapters were drafted in parallel, so a sentence like "Chapter 18 covers
strands" is a promise made by one writer about a chapter another writer had not
written yet. This finds every such promise, checks the target exists, and
prints the claim next to the target's actual headings so a wrong promise is
visible.

    .venv/bin/python tools/check_crossrefs.py
    .venv/bin/python tools/check_crossrefs.py --claims   # print every claim
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAPTERS = ROOT / "chapters"

PART_RANGE = {1: (1, 4), 2: (5, 9), 3: (10, 16), 4: (17, 21), 5: (22, 26), 6: (27, 30)}
PART_LABEL = {0: (1, 4), 1: (5, 9), 2: (10, 16), 3: (17, 21), 4: (22, 26), 5: (27, 30)}


def load() -> dict[int, tuple[Path, str, str]]:
    out = {}
    for path in sorted(CHAPTERS.glob("ch[0-3][0-9]*.qmd")):
        n = int(re.match(r"ch(\d+)", path.name).group(1))
        text = path.read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", text, re.M)
        out[n] = (path, title.group(1).strip() if title else "?", text)
    return out


def main() -> int:
    show_claims = "--claims" in sys.argv
    chapters = load()
    problems: list[str] = []
    claims: list[tuple[int, int, str]] = []

    for n, (path, _title, text) in sorted(chapters.items()):
        prose = re.sub(r"```.*?```", " ", text, flags=re.S)
        for m in re.finditer(r"Chapter (\d+)([^.;\n]{0,90})", prose):
            target = int(m.group(1))
            if target not in chapters:
                problems.append(f"ch{n:02d} refers to Chapter {target}, which does not exist")
                continue
            if target == n:
                problems.append(f"ch{n:02d} refers to itself as Chapter {target}")
            claims.append((n, target, m.group(0).strip()))

        for m in re.finditer(r"Part (\d)([^.;\n]{0,70})", prose):
            p = int(m.group(1))
            if p not in PART_LABEL:
                problems.append(f"ch{n:02d} refers to Part {p}, which does not exist")

    # Exercise numbers must match their chapter.
    for n, (path, _t, text) in sorted(chapters.items()):
        for m in re.finditer(r'\{\.exercise\s+num="(\d+)\.(\d+)"', text):
            if int(m.group(1)) != n:
                problems.append(
                    f"ch{n:02d} contains Exercise {m.group(1)}.{m.group(2)}, "
                    f"which is numbered for chapter {m.group(1)}"
                )

    # A chapter should not promise something a later chapter never mentions.
    forward = {}
    for source, target, claim in claims:
        forward.setdefault(target, []).append((source, claim))

    print(f"\n{len(chapters)} chapters, {len(claims)} cross-references\n")
    if show_claims:
        for target in sorted(forward):
            title = chapters[target][1]
            print(f"  -> Chapter {target}: {title}")
            for source, claim in forward[target]:
                print(f"       ch{source:02d}: {claim[:88]}")
            print()

    for p in problems:
        print(f"  [FAIL] {p}")
    print(f"\n{len(problems)} problem(s)\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
