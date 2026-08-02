#!/usr/bin/env python
"""Generate the parts of the back matter that must not be maintained by hand.

The dataset index and the error index are derived from the same sources the
chapters use, so they cannot drift out of step with the text. The glossary is
not generated: definitions have to be written, and a glossary assembled by a
script reads like one.

    .venv/bin/python tools/make_backmatter.py

Run it after a build, because the error index is built from the anchors the
Lua filter emits during rendering.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACK = ROOT / "backmatter"
FACTS = ROOT / "research" / "facts.jsonl"
ERRORS = ROOT / "build-logs" / "errors.tsv"


def load_facts() -> list[dict]:
    if not FACTS.exists():
        return []
    return [json.loads(l) for l in FACTS.read_text().splitlines() if l.strip()]


# ---------------------------------------------------------------------------
def dataset_index() -> str:
    """Every external source the book draws on, with the date it was checked."""
    facts = load_facts()
    by_source: dict[str, dict] = {}
    for rec in facts:
        url = rec["source_url"]
        if not url.startswith("http"):
            continue
        entry = by_source.setdefault(
            url, {"url": url, "retrieved": rec["retrieved_utc"], "methods": set(), "ids": []}
        )
        entry["methods"].add(rec["method"])
        entry["ids"].append(rec["id"])
        entry["retrieved"] = min(entry["retrieved"], rec["retrieved_utc"])

    groups: dict[str, list[dict]] = defaultdict(list)
    for entry in by_source.values():
        host = re.sub(r"^https?://", "", entry["url"]).split("/")[0]
        groups[host].append(entry)

    lines = [
        "# Dataset and source index {.unnumbered}",
        "",
        "Every external source this book states a fact from, with the date that",
        "fact was last checked against the live source. The full address is",
        "printed for readers working from paper.",
        "",
        "This page is generated from `research/facts.jsonl` by",
        "`tools/make_backmatter.py`, so it cannot fall out of step with the text.",
        "",
    ]
    for host in sorted(groups):
        lines += [f"## {host} {{.unnumbered}}", ""]
        for entry in sorted(groups[host], key=lambda e: e["url"]):
            n = len(entry["ids"])
            lines.append(
                f"- <{entry['url']}>  \n"
                f"  {n} fact{'s' if n != 1 else ''}, checked {entry['retrieved']}"
            )
        lines.append("")

    bundled = sorted((ROOT / "data").rglob("*"))
    files = [p for p in bundled if p.is_file()]
    if files:
        lines += ["## Files bundled with this book {.unnumbered}", ""]
        lines += [
            "These ship in the repository, so nothing in the book depends on a",
            "download succeeding while you are working.",
            "",
            "| File | Size |",
            "|---|---|",
        ]
        for p in files:
            size = p.stat().st_size
            human = f"{size/1_000_000:.1f} MB" if size > 1_000_000 else f"{size/1000:.0f} kB"
            lines.append(f"| `{p.relative_to(ROOT)}` | {human} |")
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
def error_index() -> str:
    """Error message to the page that addresses it."""
    lines = [
        "# Error index {.unnumbered}",
        "",
        "Every error message this book explains, in alphabetical order, with the",
        "page that explains it. Look the message up here before you search the",
        "web for it.",
        "",
    ]
    if not ERRORS.exists() or not ERRORS.read_text().strip():
        lines += [
            "*This index is generated during the build from the `If it breaks`",
            "boxes in the chapters. It is empty because the book has not been",
            "rendered yet.*",
            "",
        ]
        return "\n".join(lines) + "\n"

    seen: dict[str, str] = {}
    for line in ERRORS.read_text().splitlines():
        if "\t" not in line:
            continue
        anchor, message = line.split("\t", 1)
        seen.setdefault(message.strip(), anchor)

    # A table rather than a definition list. Pandoc renders a definition list
    # with the term hanging into the margin, which puts it outside the text
    # block, and a two-column table is easier to scan anyway.
    lines += ["| Message | Page |", "|---|---|"]
    for message in sorted(seen, key=str.lower):
        anchor = seen[message]
        safe = message.replace("|", "\\|")
        lines.append(f"| `{safe}` | \\pageref{{{anchor}}} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    BACK.mkdir(parents=True, exist_ok=True)
    (BACK / "dataset-index.qmd").write_text(dataset_index())
    (BACK / "error-index.qmd").write_text(error_index())
    print("wrote backmatter/dataset-index.qmd and backmatter/error-index.qmd")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
