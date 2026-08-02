#!/usr/bin/env python
"""Structural checks on the book's source.

These are the rules a reader would notice as a defect: code that will not fit
the column, a curly quote inside a Python snippet, a chapter with no checkpoint,
a bolded key term that never made it into the glossary, a filename label that
does not match anything in the repo.

    .venv/bin/python tools/check_content.py
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MAX_CODE_COLS = 80    # spec B4: 80 x 0.079 in = 6.33 in, inside the 6.50 in block
MAX_CODE_LINES = 34   # spec B7: a code block never breaks across a page
SMART_QUOTES = "‘’“”"


@dataclass
class Issue:
    path: str
    line: int
    rule: str
    detail: str
    severity: str = "fail"


issues: list[Issue] = []


def add(path: Path, line: int, rule: str, detail: str, severity: str = "fail") -> None:
    try:
        rel = str(path.relative_to(ROOT))
    except ValueError:
        rel = str(path)
    issues.append(Issue(rel, line, rule, detail, severity))


def chapter_files() -> list[Path]:
    return [p for p in sorted((ROOT / "chapters").glob("*.qmd")) if "smoke" not in p.name]


def content_files() -> list[Path]:
    extra: list[Path] = []
    for sub in ("frontmatter", "backmatter", "parts"):
        d = ROOT / sub
        if d.exists():
            extra += sorted(d.glob("*.qmd"))
    index = ROOT / "index.qmd"
    return chapter_files() + extra + ([index] if index.exists() else [])


def iter_fences(text: str):
    """Yield (start_line, info_string, [lines]) for every fenced block."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^(\s*)(`{3,}|~{3,})(.*)$", lines[i])
        if not m:
            i += 1
            continue
        indent, fence, info = m.groups()
        start = i + 1
        body: list[tuple[int, str]] = []
        i += 1
        while i < len(lines) and not re.match(rf"^{re.escape(indent)}{fence[0]}{{3,}}\s*$", lines[i]):
            body.append((i + 1, lines[i]))
            i += 1
        i += 1
        yield start, info.strip(), body


# ---------------------------------------------------------------------------
def check_code_blocks(path: Path, text: str) -> None:
    for start, info, body in iter_fences(text):
        is_output = ".output" in info or "cell-output" in info

        if len(body) > MAX_CODE_LINES and not is_output:
            add(path, start, "code block too long",
                f"{len(body)} lines, limit {MAX_CODE_LINES}; it would break across a page")

        for lineno, line in body:
            # Quarto cell options are directives to the build, not code. They
            # are stripped before the block is printed, so the column limit,
            # which exists so code fits the measure, does not apply to them.
            if line.lstrip().startswith("#|"):
                continue
            if len(line) > MAX_CODE_COLS:
                add(path, lineno, "code line over 80 columns",
                    f"{len(line)} chars: {line[:60]}...")
            for ch in line:
                if ch in SMART_QUOTES:
                    add(path, lineno, "smart quote inside a code block",
                        f"{ch!r} in: {line.strip()[:60]}",
                        )
                    break

        # A filename label has to point at something that really exists.
        m = re.search(r'filename="([^"]+)"', info)
        if m:
            target = ROOT / "scripts" / m.group(1)
            alt = ROOT / m.group(1)
            if not target.exists() and not alt.exists():
                add(path, start, "filename label has no file",
                    f"{m.group(1)} is labelled but not present in scripts/")


def iter_exercises(text: str):
    """Yield (number, body, line) for each exercise, tracking ::: nesting.

    A non-greedy regex stops at the first closing fence, which is the one that
    ends the .goal div, so it reports every exercise as missing every field.
    """
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r'^:::\s*\{\.exercise\s+num="([\d.]+)"', lines[i])
        if not m:
            i += 1
            continue
        num, start, depth, body = m.group(1), i + 1, 1, []
        i += 1
        while i < len(lines) and depth > 0:
            if re.match(r"^:::+\s*\{", lines[i]):
                depth += 1
            elif re.match(r"^:::+\s*$", lines[i]):
                depth -= 1
                if depth == 0:
                    break
            body.append(lines[i])
            i += 1
        yield num, "\n".join(body), start


MAX_DEF_CHARS = 150


def check_margin_defs(path: Path, text: str) -> None:
    """Margin definitions have to fit the side column.

    The side column is 1.65 in wide and 8.5 pt Inter fits roughly 30 characters
    to the line. A definition that runs past about 150 characters can be placed
    low enough on a page that \\marginpar pushes it off the bottom, which the
    layout check catches only after a full render. Catch it here instead.
    """
    for m in re.finditer(r'\{\.term\s+def="([^"]*)"', text):
        definition = m.group(1)
        if len(definition) > MAX_DEF_CHARS:
            line = text[: m.start()].count("\n") + 1
            add(path, line, "margin definition too long",
                f"{len(definition)} chars, limit {MAX_DEF_CHARS}: {definition[:60]}...")


def check_structure(path: Path, text: str) -> None:
    """Every chapter carries the skeleton the spec defines."""
    # Numbered chapter files only. "changelog.qmd" and "cheat-sheet.qmd" also
    # begin with "ch".
    if not re.match(r"ch\d\d", path.name):
        return
    # Front-of-book chapters 1-4 and the Part 1 checkpoint chapter have no
    # exercises by design; everything else does.
    if "{.checkpoint}" not in text and ":::checkpoint" not in text:
        add(path, 0, "missing checkpoint", "every chapter ends with a checkpoint")

    for num, body, line in iter_exercises(text):
        for field in ("goal", "produce", "check"):
            if not re.search(r":::+\s*\{\." + field + r"\}", body):
                add(path, line, f"exercise {num} has no .{field}",
                    "every exercise needs a goal, an artifact, and a way to tell "
                    "whether it is right")
    for attrs in re.findall(r":::\s*\{\.exercise([^}]*)\}", text):
        if "num=" not in attrs:
            add(path, 0, "exercise without a number", attrs.strip())
        if "time=" not in attrs:
            add(path, 0, "exercise without a time estimate", attrs.strip())


BANNED_OBJECTIVE_VERBS = {
    "understand", "learn", "know", "be", "gain", "explore", "appreciate",
    "master", "familiarize", "familiarise", "grasp", "realize", "recognize",
    "consider", "think", "feel", "remember",
}


def check_checkpoints(path: Path, text: str) -> None:
    """Checkpoint bullets state something observable.

    If you cannot picture somebody doing it at a keyboard while you watch, it
    is not an objective, it is a hope. This is the one style rule that a
    chapter can violate while still reading perfectly well, which is why it is
    checked mechanically.
    """
    for m in re.finditer(r":::\s*\{\.checkpoint\}(.*?):::", text, re.S):
        line = text[: m.start()].count("\n") + 1
        bullets = re.findall(r"^-\s+(.+)$", m.group(1), re.M)
        if not bullets:
            add(path, line, "empty checkpoint", "no bullets")
        for b in bullets:
            first = b.strip().split()[0].lower().strip(",.")
            if first in BANNED_OBJECTIVE_VERBS:
                add(path, line, "checkpoint is not observable",
                    f"starts with '{first}': {b.strip()[:60]}")


def check_glossary(files: list[Path]) -> None:
    """Every term marked up in the text has a glossary entry, and vice versa."""
    glossary = ROOT / "backmatter" / "glossary.qmd"
    if not glossary.exists():
        add(ROOT / "backmatter" / "glossary.qmd", 0, "glossary missing",
            "backmatter/glossary.qmd has not been written yet", severity="warn")
        return

    gtext = glossary.read_text(encoding="utf-8")
    entries = {
        m.group(1).strip().lower()
        for m in re.finditer(r"^\*\*(.+?)\*\*", gtext, re.M)
    }

    used: dict[str, str] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"\[([^\]]+)\]\{\.term\b", text):
            used[m.group(1).strip().lower()] = str(path.name)

    for term, where in sorted(used.items()):
        if term not in entries:
            add(ROOT / "backmatter" / "glossary.qmd", 0, "term missing from glossary",
                f"'{term}' is marked up in {where} but has no glossary entry")

    for entry in sorted(entries):
        if entry not in used:
            add(ROOT / "backmatter" / "glossary.qmd", 0, "glossary entry never used",
                f"'{entry}' is defined but never marked up in the text", severity="warn")


def check_glossary_anchors(files: list[Path]) -> None:
    """Every marked-up term must resolve to a glossary anchor.

    The filter builds the link target from the term text and the anchor from
    the glossary entry text, using the same slug rule. If the two texts differ
    at all, the link points at nothing and the PDF ships with a dead reference
    that no reader can distinguish from a working one.
    """
    glossary = ROOT / "backmatter" / "glossary.qmd"
    if not glossary.exists():
        return

    def slug(s: str) -> str:
        return re.sub(r"[^0-9A-Za-z]+", "-", s.lower()).strip("-")

    entries = {
        slug(m.group(1))
        for m in re.finditer(r"^\*\*(.+?)\*\*", glossary.read_text(), re.M)
    }
    for path in files:
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"\[([^\]]+)\]\{\.term\b", text):
            if slug(m.group(1)) not in entries:
                line = text[: m.start()].count("\n") + 1
                add(path, line, "term link resolves to nothing",
                    f"'{m.group(1)}' has no glossary entry with a matching anchor")


def check_facts_cited(files: list[Path]) -> None:
    """Numbers in the text should trace to research/facts.jsonl.

    This is advisory. It flags four-or-more digit numbers that do not appear as
    a value in the fact registry, which is how a hallucinated accession length
    or coordinate gets caught before it reaches a reader.
    """
    import json

    registry = ROOT / "research" / "facts.jsonl"
    if not registry.exists():
        return
    known: set[str] = set()
    for line in registry.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        val = rec["value"]
        for item in (val if isinstance(val, list) else [val]):
            known.add(str(item))
            known.update(re.findall(r"\d[\d,]{3,}", str(item)))
    known = {k.replace(",", "") for k in known}

    for path in files:
        text = path.read_text(encoding="utf-8")
        prose = re.sub(r"```.*?```", " ", text, flags=re.S)
        # A number inside a URL is part of an address, not a claim.
        prose = re.sub(r"<https?://\S+>|https?://\S+", " ", prose)
        # A number the chapter derives on the page, or deliberately shows as a
        # wrong answer, is declared with an allow comment so it is auditable
        # rather than silently exempt.
        allowed = set()
        for m in re.finditer(r"<!--\s*nlr-allow:\s*([^>]*?)\s*-->", text):
            allowed.update(x.strip().replace(",", "") for x in m.group(1).split())
        for m in re.finditer(r"(?<![\w.])(\d[\d,]{3,})(?![\w])", prose):
            raw = m.group(1).replace(",", "")
            if raw in known or raw in allowed:
                continue
            if raw.startswith(("19", "20")) and len(raw) == 4:  # a year
                continue
            line = text[: m.start()].count("\n") + 1
            add(path, line, "unverified number",
                f"{m.group(1)} is not in research/facts.jsonl", severity="warn")


def main() -> int:
    files = content_files()
    if not files:
        print("no content files yet")
        return 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        check_code_blocks(path, text)
        check_structure(path, text)
        check_margin_defs(path, text)
        check_checkpoints(path, text)
    check_glossary(files)
    check_glossary_anchors(files)
    check_facts_cited(files)

    fails = [i for i in issues if i.severity == "fail"]
    warns = [i for i in issues if i.severity == "warn"]
    for group, label in ((fails, "FAIL"), (warns, "warn")):
        for i in group:
            loc = f"{i.path}:{i.line}" if i.line else i.path
            print(f"  [{label}] {loc}  {i.rule}: {i.detail}")
    print(f"\n{len(files)} file(s): {len(fails)} failures, {len(warns)} warnings")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
