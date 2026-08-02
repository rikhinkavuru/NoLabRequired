#!/usr/bin/env python
"""Generate the companion answer sheet readers copy and fill in.

Spec B9 rejects fillable PDF form fields, because they render inconsistently
across readers and break entirely in some mobile viewers, and asks for a
companion document instead. This is it, generated from the exercises themselves
so it cannot fall out of step with the book.

    .venv/bin/python tools/make_answer_sheet.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "answers" / "answer-sheet-template.md"

EX = re.compile(
    r':::\s*\{\.exercise\s+num="([\d.]+)"\s+time="([^"]+)"[^}]*\}(.*?)\n:::\s*\n\s*\n',
    re.S,
)
FIELD = re.compile(r':::\s*\{\.goal\}\s*(.*?)\s*:::', re.S)


def main() -> int:
    lines = [
        "# Answer sheet",
        "",
        "Copy this into whatever you write in. It has a space for every exercise",
        "in the book, in order, with the time the book budgets for it.",
        "",
        "Two things worth doing as you go. Write the date next to each answer, so",
        "that when you come back after a gap you can see where you stopped. And",
        "when an answer surprises you, write down what you expected instead. That",
        "second note is worth more later than the answer is.",
        "",
        "The worked answers are in this same folder, one file per chapter.",
        "",
        "---",
        "",
    ]

    total = 0
    minutes = 0
    for path in sorted((ROOT / "chapters").glob("ch[0-3][0-9]*.qmd")):
        text = path.read_text(encoding="utf-8")
        n = int(re.match(r"ch(\d+)", path.name).group(1))
        title = re.search(r"^# (.+)$", text, re.M)
        found = EX.findall(text)
        if not found:
            continue
        lines += [f"## Chapter {n}. {title.group(1).strip() if title else ''}", ""]
        for num, time, body in found:
            total += 1
            m = re.search(r"(\d+)", time)
            if m:
                minutes += int(m.group(1))
            goal = FIELD.search(body)
            goal_text = " ".join(goal.group(1).split()) if goal else ""
            lines += [
                f"### Exercise {num}  ({time})",
                "",
                f"*{goal_text}*" if goal_text else "",
                "",
                "Date attempted:",
                "",
                "Answer:",
                "",
                "",
                "",
                "",
                "What I expected instead, if it differed:",
                "",
                "",
                "---",
                "",
            ]

    hours = minutes / 60
    lines[10:10] = [
        f"There are {total} exercises. The times printed in the book add up to "
        f"about {hours:.0f} hours, which is roughly {hours/3:.0f} weeks at three "
        "hours a week, and it will take longer than that.",
        "",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT.relative_to(ROOT)}: {total} exercises, {minutes} budgeted minutes ({hours:.1f} hours)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
