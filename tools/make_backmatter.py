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
def slugify(err: str) -> str:
    """The anchor slug, matching filters/nlr-components.lua exactly."""
    slug = re.sub(r"[^0-9a-z]+", "-", err.lower()).strip("-")
    return slug[:60]


LITERAL_PREFIX = (
    "Traceback", "Killed", "command not found", "zsh:", "bash:", "fatal:",
    "usage:", "error:", "warning:",
)


def is_literal(message: str) -> bool:
    """True when the machine printed this, false when somebody described it."""
    if " " not in message:
        return True
    if re.match(r"^[A-Za-z]*(Error|Warning|Exception)\b", message):
        return True
    if re.match(r"^\d{3}\b", message):
        return True
    return message.startswith(LITERAL_PREFIX)


def error_index() -> str:
    """Error message to the page that addresses it."""
    lines = [
        "# Error index {.unnumbered}",
        "",
        "Every error message this book explains and every stuck moment it names,",
        "in alphabetical order, with the page that deals with it. Look yours up",
        "here before you search the web for it. Anything set in code type is what",
        "the machine prints; the rest describes a situation.",
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

    # Which chapter each entry lives in, read straight off the sources. The
    # filter cannot supply it: by the time it runs, Quarto has preprocessed the
    # chapter into a temp file and the original name is gone from input_files.
    source_of = {}
    for qmd in sorted(Path("chapters").glob("*.qmd")):
        # The value may contain escaped quotes: err="KeyError: \"['x'] not in
        # index\"". A [^"]* pattern stops at the first inner one and slugs the
        # truncated string, which then matches no anchor.
        for err in re.findall(r'errfix err="((?:[^"\\]|\\.)*)"', qmd.read_text()):
            err = err.replace('\\"', '"').replace("\\\\", "\\")
            source_of[slugify(err)] = qmd.name

    seen: dict[str, tuple[str, str]] = {}
    for line in ERRORS.read_text().splitlines():
        if "\t" not in line:
            continue
        anchor, message = line.split("\t", 1)
        anchor = anchor.strip()
        seen.setdefault(message.strip(),
                        (anchor, source_of.get(anchor[len("err-"):], "")))

    # A table rather than a definition list. Pandoc renders a definition list
    # with the term hanging into the margin, which puts it outside the text
    # block, and a two-column table is easier to scan anyway.
    lines += ["| Message or situation | Page |", "|---|---:|"]
    # Sort on letters and digits only. With punctuation significant,
    # "AttributeError: PathCollection.set()" sorted after both quoted
    # AttributeErrors instead of between them.
    def sort_key(msg: str) -> str:
        return re.sub(r"[^0-9a-z]+", " ", msg.lower()).strip()

    for message in sorted(seen, key=sort_key):
        anchor, source = seen[message]
        safe = message.replace("|", "\\|")
        # Just over half of these entries are situations somebody wrote down,
        # not text an interpreter printed. Setting "A paper reports 98 percent
        # homology and you need to quote it" in monospace says it is a literal
        # string, which is false, and costs the column about a fifth of its
        # width on top of that.
        cell = f"`{safe}`" if is_literal(message) else safe
        # The message links to the entry as well as carrying a page number.
        # \pageref is LaTeX-only, so in the web edition the second column
        # rendered empty and the index was a list of messages pointing nowhere.
        # Quarto rewrites a .qmd target to .html for the site and to a
        # \\hyperref for the PDF, so one link serves both editions.
        target = f"../chapters/{source}#{anchor}" if source else f"#{anchor}"
        lines.append(f"| [{cell}]({target}) | \\pageref{{{anchor}}} |")
    lines.append("")
    # Without this pandoc splits the table 50/50 and reserves two and a half
    # inches of the page to hold a three-digit number, which leaves every row
    # blank across its right half.
    lines.append(': {tbl-colwidths="[88,12]"}')
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
