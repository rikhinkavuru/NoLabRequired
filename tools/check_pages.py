#!/usr/bin/env python
"""Report how many pages each chapter actually occupies, against its budget.

A chapter that runs to fourteen pages is not a long chapter. It is two
chapters, or a chapter with a section that should have been cut, and it is
easier to see that here than by reading.

    .venv/bin/python tools/check_pages.py [pdf]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent

# From research/BEAT_SHEET.md. Chapters may land within one page either way.
BUDGET = {
    1: 3, 2: 4, 3: 3, 4: 4,
    5: 8, 6: 8, 7: 8, 8: 8, 9: 6,
    10: 5, 11: 9, 12: 8, 13: 9, 14: 6, 15: 9, 16: 10,
    17: 8, 18: 10, 19: 10, 20: 10, 21: 10,
    22: 6, 23: 7, 24: 12, 25: 7, 26: 8,
    27: 6, 28: 6, 29: 5, 30: 3,
}
TOLERANCE = 2


def outline_entries(reader: PdfReader):
    """Chapter-level bookmarks, as (title, page index) pairs, in reading order.

    Parts sit at the top level and chapters one level inside them, so a chapter
    is depth 1 and its own sections are deeper. Part entries are kept as well,
    unnumbered, because the last chapter of a part needs the next part to bound
    it or it absorbs everything after it.
    """
    out: list[tuple[str, int]] = []

    def walk(items, depth=0):
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
                continue
            if depth > 1:
                continue
            try:
                out.append((str(item.title), reader.get_destination_page_number(item)))
            except Exception:
                pass

    walk(reader.outline or [])
    return sorted(out, key=lambda t: t[1])


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "_book/bioinformatics-workbook-v1.0.pdf"
    reader = PdfReader(path)
    total = len(reader.pages)
    entries = outline_entries(reader)

    # Every top-level entry is a boundary; only the numbered ones get reported.
    boundaries = [page for _, page in entries] + [total]
    starts: list[tuple[int, str, int, int]] = []
    for idx, (title, page) in enumerate(entries):
        m = re.match(r"^(\d+)\s+(.*)$", title.strip())
        if not m:
            continue
        nxt = next((p for p in boundaries if p > page), total)
        starts.append((int(m.group(1)), m.group(2), page, nxt))

    if not starts:
        print("no numbered chapters found in the bookmarks")
        return 0

    print(f"\n{path}  ({total} pages)\n")
    print(f"  {'ch':>3}  {'pages':>5}  {'budget':>6}       title")
    over = 0
    content_pages = 0
    for n, title, start, end in starts:
        pages = end - start
        content_pages += pages
        budget = BUDGET.get(n)
        if budget is None:
            flag = "    "
            note = ""
        elif abs(pages - budget) <= TOLERANCE:
            flag = "    "
            note = f"{budget:>6}"
        else:
            flag = "OVER" if pages > budget else "under"
            over += 1
            note = f"{budget:>6}"
        print(f"  {n:>3}  {pages:>5}  {note}  {flag:>5}  {title[:52]}")

    print(f"\n  {len(starts)} chapters, {content_pages} pages of chapters, {total} pages total")
    if over:
        print(f"  {over} chapter(s) more than {TOLERANCE} pages from budget")
    written = len(starts)
    if written < 30:
        per = content_pages / written
        projected = per * 30 + (total - content_pages)
        print(f"  at {per:.1f} pages a chapter, 30 chapters projects to about {projected:.0f} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
