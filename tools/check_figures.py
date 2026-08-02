#!/usr/bin/env python
"""Every figure carries alt text and a caption.

Spec B9 requires alt text on every figure. A caption says what the figure is
for; alt text says what is in it. A reader using a screen reader gets only the
second, so a figure with a caption and no alt text is a figure they cannot see
at all.

    .venv/bin/python tools/check_figures.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    problems: list[str] = []
    figures = 0

    for path in sorted((ROOT / "chapters").glob("ch[0-3][0-9]*.qmd")) + \
                sorted((ROOT / "backmatter").glob("*.qmd")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)

        # Executed cells that produce a figure declare a caption.
        for m in re.finditer(r"```\{python\}\n((?:#\|.*\n)*)", text):
            block = m.group(1)
            if "fig-cap:" not in block:
                continue
            figures += 1
            line = text[: m.start()].count("\n") + 1
            if "fig-alt:" not in block:
                problems.append(f"{rel}:{line}  figure has a caption but no fig-alt")

        # Static images.
        for m in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", text):
            figures += 1
            line = text[: m.start()].count("\n") + 1
            if not m.group(1).strip():
                problems.append(f"{rel}:{line}  image has no alt text: {m.group(2)}")

    # If the web edition has been built, confirm the glossary links land
    # somewhere. Pandoc silently drops an empty anchor span, and a link to a
    # missing anchor looks identical to a working one until it is pressed.
    built = ROOT / "_book" / "backmatter" / "glossary.html"
    if built.exists():
        html = built.read_text(encoding="utf-8", errors="replace")
        anchors = set(re.findall(r'id="(gloss-[a-z0-9-]+)"', html))
        targets = set()
        for f in (ROOT / "_book" / "chapters").glob("*.html"):
            targets |= set(re.findall(r'href="#(gloss-[a-z0-9-]+)"', f.read_text(encoding="utf-8", errors="replace")))
        dangling = sorted(targets - anchors)
        if dangling:
            problems.append(
                f"_book: {len(dangling)} glossary link(s) point at anchors that "
                f"do not exist, e.g. {dangling[:3]}"
            )
        else:
            print(f"  {len(targets)} glossary links resolve to {len(anchors)} anchors")

    for p in problems:
        print(f"  [FAIL] {p}")
    print(f"\n{figures - len([x for x in problems if 'alt text' in x])}/{figures} figures carry alt text\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
