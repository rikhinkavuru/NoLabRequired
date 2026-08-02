#!/usr/bin/env python
"""Check that every external link in the book still resolves.

A workbook that sends a beginner to a 404 has failed them at the exact moment
they were least able to recover. Run this before every release; the results
feed the "last checked" dates in the dataset index.

    .venv/bin/python tools/check_links.py            # all content
    .venv/bin/python tools/check_links.py --json out.json
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "no-lab-required-workbook/1.0 (link check; rikhin@virahacks.com)"

URL_RE = re.compile(r"https?://[^\s<>\)\]\"'`|]+")


# research/ holds working notes, not shipped content. Forum threads there are
# behind bot protection and return 403 to any automated request, which would
# make this check permanently red for links no reader ever follows.
SKIP_DIRS = {"_book", ".venv", "research", "_freeze", ".quarto"}


def collect(include_research: bool = False) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    globs = ["*.qmd", "**/*.qmd", "*.md", "docs/*.md", "README.md"]
    seen: set[Path] = set()
    skip = SKIP_DIRS - ({"research"} if include_research else set())
    for pattern in globs:
        for path in ROOT.glob(pattern):
            if path in seen or skip & set(path.parts):
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8", errors="replace")
            for m in URL_RE.finditer(text):
                url = m.group(0).rstrip(".,;:")
                line = text[: m.start()].count("\n") + 1
                found.setdefault(url, []).append(f"{path.name}:{line}")
    return found


def probe(url: str) -> tuple[str, int | str]:
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return url, resp.status
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in (403, 405, 501):
                continue  # some hosts refuse HEAD; retry as GET
            return url, exc.code
        except Exception as exc:  # noqa: BLE001
            if method == "GET":
                return url, type(exc).__name__
    return url, "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write full results here")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    urls = collect(include_research="--research" in sys.argv)
    if not urls:
        print("no links found")
        return 0
    print(f"checking {len(urls)} unique links\n")

    results: dict[str, int | str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for url, status in pool.map(probe, urls):
            results[url] = status

    # The book's own repository and site do not exist until it is published.
    # They are reported as pending rather than as failures, so this check is
    # usable as a release gate before the first release rather than only after.
    OWN = ("github.com/rikhinkavuru/NoLabRequired",
           "rikhinkavuru.github.io/NoLabRequired")
    bad, pending, blocked = {}, {}, {}
    for u, s in results.items():
        if isinstance(s, int) and 200 <= s < 400:
            continue
        if any(o in u for o in OWN):
            pending[u] = s
        elif s in (403, 429):
            # The server answered and refused the robot. Publishers routinely
            # block automated requests, so this says nothing about whether the
            # page is there. A 404 does; a 403 does not.
            blocked[u] = s
        else:
            bad[u] = s
    for url in sorted(bad):
        print(f"  [{bad[url]}] {url}")
        for where in urls[url][:4]:
            print(f"           {where}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "checked_utc": datetime.now(timezone.utc).isoformat(),
                    "results": {u: {"status": s, "cited_in": urls[u]} for u, s in results.items()},
                },
                indent=2,
            )
        )

    if blocked:
        print("\n  refused the robot, check these by hand in a browser:")
        for url in sorted(blocked):
            print(f"    [{blocked[url]}] {url}")

    if pending:
        print("\n  pending, these come into existence at publication:")
        for url in sorted(pending):
            print(f"    [{pending[url]}] {url}")

    checked = len(urls) - len(pending) - len(blocked)
    print(f"\n{checked - len(bad)}/{checked} external links OK, "
          f"{len(blocked)} refused the robot, {len(pending)} pending publication")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
