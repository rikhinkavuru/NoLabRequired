#!/usr/bin/env python
"""Prose linter for the workbook.

The voice rules in research/STYLE_BIBLE.md are binding, and most of them are
mechanically checkable. This catches the ones that are: the tells that make
technical writing read as machine-generated, plus the measurable targets for
sentence length, address, and paragraph shape.

It only ever looks at prose. Fenced code, inline code, YAML headers, URLs,
LaTeX passthrough and table rows are stripped before any rule runs, because a
BLAST output line or a Python traceback is not prose and must not be scored
like it.

    .venv/bin/python tools/check_prose.py chapters/ch05-reading-a-gene.qmd
    .venv/bin/python tools/check_prose.py --all
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Finding:
    line: int
    rule: str
    severity: str  # "fail" | "warn"
    excerpt: str
    note: str = ""


@dataclass
class Report:
    path: Path
    findings: list[Finding] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def failures(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "fail"]


# ---------------------------------------------------------------------------
# Stripping: reduce a .qmd to the prose a reader actually reads
# ---------------------------------------------------------------------------
def prose_lines(text: str) -> list[tuple[int, str]]:
    """Return (1-based line number, prose text) for every prose line.

    Line-level, so the character and phrase rules can report a real line number.
    Sentence-level rules must use `paragraphs()` instead: markdown is hard
    wrapped, so a single sentence usually spans three lines and measuring
    sentence length off raw lines reports roughly a third of the truth.
    """
    out: list[tuple[int, str]] = []
    in_fence = False
    in_yaml = False
    fence_re = re.compile(r"^\s*(```|~~~)")

    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\n")

        if i == 1 and line.strip() == "---":
            in_yaml = True
            continue
        if in_yaml:
            if line.strip() in ("---", "..."):
                in_yaml = False
            continue

        if fence_re.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        stripped = line.strip()
        if not stripped:
            continue
        # Div fences, headings, table rows, HTML/LaTeX passthrough, list markers
        if stripped.startswith(":::") or stripped.startswith("#"):
            continue
        if stripped.startswith("|") or re.match(r"^[-:| ]+$", stripped):
            continue
        if stripped.startswith("<") or stripped.startswith("\\"):
            continue
        if re.match(r"^\[\^[^\]]+\]:", stripped):  # footnote definition still counts
            stripped = re.sub(r"^\[\^[^\]]+\]:\s*", "", stripped)

        # Inline code, URLs, link targets, images: not prose
        s = re.sub(r"`[^`]*`", " ", stripped)
        s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
        s = re.sub(r"<https?://[^>]+>", " ", s)
        s = re.sub(r"https?://\S+", " ", s)
        s = re.sub(r"\{[^}]*\}", " ", s)  # pandoc attributes
        s = re.sub(r"^\s*[-*+]\s+", "", s)
        s = re.sub(r"^\s*\d+\.\s+", "", s)
        s = s.strip()
        if s:
            out.append((i, s))
    return out


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

# Hard bans. The em dash never appears in this book's prose: it is the single
# loudest machine tell, and every use of it has a comma, a full stop, a colon or
# a pair of brackets that does the job without the tell. The en dash is legal
# only where typography requires it, between numbers in a range.
BANNED_CHARS = {"—": "em dash"}
EN_DASH_OK = re.compile(r"(?<=\d)–(?=\d)")

BANNED_PHRASES = [
    # significance theatre
    (r"\bplays? (?:a |an )?(?:crucial|vital|key|pivotal|significant|important) role\b", "hollow significance"),
    (r"\bis a testament to\b", "hollow significance"),
    # Verb usage only. "letters, digits and underscores" is the character.
    (r"\bunderscor(?:es|ing|ed)\s+(?:the|that|how|why|a|an)\b", "hollow significance"),
    (r"\bhighlight(?:s|ing)? the (?:importance|need|fact)\b", "hollow significance"),
    (r"\bserves as a reminder\b", "hollow significance"),
    (r"\bcannot be overstated\b", "hollow significance"),
    (r"\bin the (?:world|realm|landscape|field) of\b", "throat-clearing opener"),
    (r"\bin today'?s\b", "throat-clearing opener"),
    (r"\bit'?s (?:worth|important) (?:noting|to note)\b", "throat-clearing"),
    (r"\bwhen it comes to\b", "throat-clearing"),
    # LLM vocabulary
    (r"\bdelv(?:e|es|ing)\b", "LLM vocabulary"),
    (r"\bleverag(?:e|es|ing)\b", "LLM vocabulary"),
    (r"\bseamless(?:ly)?\b", "LLM vocabulary"),
    (r"\bcutting[- ]edge\b", "LLM vocabulary"),
    (r"\bgame[- ]chang(?:er|ing)\b", "LLM vocabulary"),
    (r"\btapestry\b", "LLM vocabulary"),
    (r"\brealm\b", "LLM vocabulary"),
    (r"\bembark\b", "LLM vocabulary"),
    (r"\bfoster(?:ing|s)?\b", "LLM vocabulary"),
    (r"\bunlock(?:ing|s)?\b", "LLM vocabulary"),
    (r"\belevat(?:e|es|ing)\b", "LLM vocabulary"),
    (r"\bmeticulous(?:ly)?\b", "LLM vocabulary"),
    (r"\bnavigat(?:e|ing) the\b", "LLM vocabulary"),
    (r"\bharness(?:ing|es)?\b", "LLM vocabulary"),
    (r"\ba myriad of\b", "LLM vocabulary"),
    (r"\bplethora\b", "LLM vocabulary"),
    (r"\bpar excellence\b", "LLM vocabulary"),
    # negative parallelism
    (r"\b(?:it'?s|this is|that'?s) not (?:just |merely |simply |only )?\w[^.;]{0,60}[,;] (?:it'?s|this is|that'?s)\b", "negative parallelism"),
    (r"\bnot (?:just|merely|simply|only) [^.;]{2,60}\bbut (?:also )?\b", "negative parallelism"),
    (r"\bisn'?t about [^.;]{2,60}[,;] it'?s about\b", "negative parallelism"),
    # closing restatement
    (r"^(?:In (?:summary|conclusion|short)|Overall|To sum up|Ultimately|In essence)\b", "closing restatement"),
    # hedging stacks
    (r"\b(?:may|might|could) (?:potentially|possibly|perhaps)\b", "hedge stack"),
    (r"\bsomewhat of a\b", "hedge stack"),
    # false enthusiasm
    (r"\b(?:Let'?s dive in|dive deep|deep dive)\b", "false enthusiasm"),
    (r"\bexciting (?:world|journey|field)\b", "false enthusiasm"),
]

# Budgeted, not banned outright.
BUDGETED = [
    (r"\brobust\b", "robust", 1),
    (r"\bcrucial\b", "crucial", 0),
    (r"\bcomprehensive\b", "comprehensive", 1),
    (r"\bpowerful\b", "powerful", 2),
    (r"\bsimply\b", "simply", 1),
    (r"\bjust\b", "just", 8),
    (r"\bvery\b", "very", 3),
    (r"\bLet'?s\b", "let's", 6),
    (r"\bof course\b", "of course", 1),
]

# The book is set en-US on US Letter by a US author. Mixed spelling inside one
# book is a defect whichever side you pick, so the side is picked here.
BRITISH = {
    r"\bmaths\b": "math",
    r"\bcolour(s|ed|ing|less)?\b": "color",
    r"\bbehaviour(s|al)?\b": "behavior",
    r"\bfavour(s|ed|ing|ite)?\b": "favor",
    r"\blabell(ed|ing)\b": "labeled / labeling",
    r"\bmodell(ed|ing)\b": "modeled / modeling",
    r"\btravell(ed|ing)\b": "traveled / traveling",
    r"\bcentre(s|d)?\b": "center",
    r"\bmetre(s)?\b": "meter",
    r"\blicence\b": "license",
    r"\bpractise(s|d)?\b": "practice",
    r"\bwhilst\b": "while",
    r"\bamongst\b": "among",
    r"\blearnt\b": "learned",
    r"\bspelt\b": "spelled",
    r"\b(summari|organi|recogni|normali|utili|emphasi|apologi|categori|characteri|minimi|maximi|optimi|prioriti|speciali|standardi|visuali)s(e|es|ed|ing)\b": "-ize",
    r"\banalys(e|es|ed|ing)\b": "analyze",
}

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")
PARTICIPIAL_OPENER = re.compile(
    r"^(?!According|Following|During|Depending|Regarding|Including)"
    r"([A-Z][a-z]+(?:ing))\b[^.,;]{0,60},\s"
)


LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")


def paragraphs(text: str, prose: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Rejoin hard-wrapped prose lines into the paragraphs they belong to.

    A blank line ends a paragraph, and so does the start of a new list item:
    bullets are not separated by blank lines, and gluing six of them together
    produces one fictitious 80-word sentence.
    """
    raw = text.splitlines()
    kept = {ln for ln, _ in prose}
    lookup = dict(prose)
    out: list[tuple[int, str]] = []
    current: list[str] = []
    start = 0

    def flush() -> None:
        nonlocal current
        if current:
            out.append((start, " ".join(current)))
            current = []

    for i in range(1, len(raw) + 1):
        if i not in kept:
            flush()
            continue
        if LIST_ITEM.match(raw[i - 1]):
            flush()
        if not current:
            start = i
        current.append(lookup[i])
    flush()
    # Pandoc attribute blocks are stripped again here, after joining. A
    # {.term def="..."} span routinely wraps across two hard-wrapped lines, and
    # a per-line strip cannot see it, which inflates both the word count and
    # the measured sentence length.
    return [(ln, re.sub(r"\{[^{}]*\}", " ", text).replace("  ", " ").strip()) for ln, text in out]


ABBREV = re.compile(r"\b(?:e\.g|i\.e|cf|vs|etc|Dr|Mr|Ms|St|Fig|approx|No)\.$")


def sentences(paras: list[tuple[int, str]]) -> list[tuple[int, str]]:
    out = []
    for lineno, text in paras:
        parts = SENTENCE_SPLIT.split(text)
        merged: list[str] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Do not split on a full stop that belongs to an abbreviation.
            # A decimal point never triggers a split in the first place, because
            # the split pattern requires whitespace after the stop; guarding for
            # one instead glued together every sentence that ended in a number.
            if merged and ABBREV.search(merged[-1]):
                merged[-1] = merged[-1] + " " + part
            else:
                merged.append(part)
        for part in merged:
            out.append((lineno, part))
    return out


def words(s: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", s)


def check_file(path: Path, *, strict: bool = True) -> Report:
    text = path.read_text(encoding="utf-8")
    prose = prose_lines(text)
    rep = Report(path=path)
    sents = sentences(paragraphs(text, prose))
    all_words = [w.lower() for _, s in sents for w in words(s)]
    n_words = len(all_words) or 1

    # --- hard-banned characters -------------------------------------------
    for lineno, line in prose:
        for ch, name in BANNED_CHARS.items():
            if ch in line:
                rep.findings.append(
                    Finding(lineno, name, "fail", line[:100],
                            "Hard cut. Rewrite with a comma, a full stop, or a colon.")
                )
        for pattern, american in BRITISH.items():
            m = re.search(pattern, line, re.I)
            if m:
                rep.findings.append(
                    Finding(lineno, "British spelling", "fail", m.group(0),
                            f"This book is set en-US. Use {american}.")
                )
        if "–" in EN_DASH_OK.sub("", line):
            rep.findings.append(
                Finding(lineno, "en dash outside a number range", "fail", line[:100],
                        "En dashes are for numeric ranges only.")
            )

    # --- banned phrases ----------------------------------------------------
    for lineno, line in prose:
        for pattern, label in BANNED_PHRASES:
            m = re.search(pattern, line, re.I)
            if m:
                rep.findings.append(Finding(lineno, label, "fail", m.group(0)[:90]))

    # --- budgeted words ----------------------------------------------------
    joined = " ".join(s for _, s in sents)
    per_1k = 1000.0 / n_words
    for pattern, label, budget in BUDGETED:
        hits = re.findall(pattern, joined, re.I)
        allowed = max(budget, int(budget * n_words / 1000) if budget else 0)
        if len(hits) > allowed:
            rep.findings.append(
                Finding(0, f"over budget: {label}", "warn",
                        f"{len(hits)} uses, budget {allowed}")
            )

    # --- rule of three -----------------------------------------------------
    # "a, b, and c" where all three items are one abstract word. Concrete
    # technical triples ("blastn, blastp, and blastx") are fine and excluded by
    # requiring every item to be a plain lowercase word with no digits.
    tricolon = re.compile(
        r"\b([a-z]{4,})\s*,\s*([a-z]{4,})\s*,\s+and\s+([a-z]{4,})\b"
    )
    for lineno, s in sents:
        m = tricolon.search(s)
        if m and len({m.group(1), m.group(2), m.group(3)}) == 3:
            rep.findings.append(
                Finding(lineno, "rule of three", "warn", m.group(0)[:80],
                        "Three abstract items in a row is a cadence tell. Cut to two or make one concrete.")
            )

    # --- sentence-final significance tail ----------------------------------
    # Measured at 2-5x the human rate in LLM prose (Reinhart et al.), and it
    # survives any de-slopping pass that only greps for vocabulary. The shape is
    # a complete sentence followed by a comma and a participial clause that adds
    # no information: "..., making it a powerful tool for researchers."
    tail = re.compile(
        r",\s+(?:making|allowing|enabling|ensuring|highlighting|underscoring|"
        r"reflecting|showcasing|demonstrating|providing|offering|creating|"
        r"helping|leading|resulting|contributing|paving)\b[^,]*\.$"
    )
    tails = 0
    for lineno, s in sents:
        if tail.search(s):
            tails += 1
            rep.findings.append(
                Finding(lineno, "significance tail", "fail", s[-80:],
                        "Sentence-final '-ing' clause that adds nothing. Cut it or make it a real clause.")
            )

    # --- procedure-shaming adverbs ----------------------------------------
    # Google's own style guide bans these by name. Every one of them tells a
    # stuck reader that their difficulty is a personal failing.
    for lineno, s in sents:
        m = re.search(r"\b(?:simply|easily|just simply|it'?s easy|it'?s that simple|straightforward(?:ly)?|obviously|of course,|clearly,)\b", s, re.I)
        if m:
            rep.findings.append(
                Finding(lineno, "shaming adverb", "fail", m.group(0),
                        "Bans from Google's developer style guide. If it were easy the reader would not be reading.")
            )

    # --- refusal to make a call -------------------------------------------
    for lineno, s in sents:
        if re.search(r"\b(?:depends on your (?:use case|needs)|there'?s no right answer|whichever you prefer|both are valid)\b", s, re.I):
            rep.findings.append(
                Finding(lineno, "refuses to choose", "fail", s[:90],
                        "A beginner cannot evaluate a trade-off they have never seen. Pick one and say why.")
            )

    # --- participial openers ----------------------------------------------
    participial = 0
    for lineno, s in sents:
        if PARTICIPIAL_OPENER.match(s):
            participial += 1
            if participial > 2:
                rep.findings.append(
                    Finding(lineno, "participial opener", "warn", s[:80],
                            "Third or later '-ing ...,' sentence opener in this file.")
                )

    # --- sentence length ---------------------------------------------------
    lengths = [len(words(s)) for _, s in sents]
    if lengths:
        mean = sum(lengths) / len(lengths)
        longest = max(lengths)
        rep.stats["sentences"] = len(lengths)
        rep.stats["words"] = n_words
        rep.stats["mean_sentence_words"] = round(mean, 1)
        rep.stats["longest_sentence_words"] = longest
        rep.stats["pct_over_30_words"] = round(
            100 * sum(1 for x in lengths if x > 30) / len(lengths), 1
        )
        rep.stats["pct_under_10_words"] = round(
            100 * sum(1 for x in lengths if x < 10) / len(lengths), 1
        )
        if mean > 22:
            rep.findings.append(Finding(0, "mean sentence length", "warn", f"{mean:.1f} words (target 14-20)"))
        if longest > 45:
            worst = max(sents, key=lambda t: len(words(t[1])))
            rep.findings.append(Finding(worst[0], "sentence too long", "fail", worst[1][:110],
                                        f"{longest} words. Split it."))
        if rep.stats["pct_under_10_words"] < 12 and len(lengths) > 25:
            rep.findings.append(Finding(0, "no short sentences", "warn",
                                        f"only {rep.stats['pct_under_10_words']}% under 10 words",
                                        "Uniform sentence length is the strongest machine tell there is."))

    # --- second person -----------------------------------------------------
    you = sum(1 for w in all_words if w in ("you", "your", "you're", "yours"))
    rep.stats["you_per_1k"] = round(you * per_1k, 1)
    if len(lengths) > 25 and you * per_1k < 8:
        rep.findings.append(Finding(0, "second person too rare", "warn",
                                    f"{you * per_1k:.1f} per 1000 words",
                                    "This is a workbook. Address the reader."))

    # --- repeated sentence openers ----------------------------------------
    openers: dict[str, int] = {}
    for _, s in sents:
        w = words(s)
        if w:
            openers[w[0].lower()] = openers.get(w[0].lower(), 0) + 1
    # Reference pages repeat an opener on purpose: every glossary entry ends
    # "See Chapter N", and that consistency is the point of a glossary.
    is_reference = "backmatter" in str(path)
    for opener, count in openers.items():
        if is_reference:
            break
        if count >= 5 and opener not in ("the", "a", "if", "you", "it", "this"):
            rep.findings.append(Finding(0, "repeated sentence opener", "warn",
                                        f"{count} sentences start with '{opener}'"))

    # --- passive voice (heuristic) -----------------------------------------
    passive = len(re.findall(r"\b(?:is|are|was|were|be|been|being)\s+\w+(?:ed|en)\b", joined, re.I))
    rep.stats["passive_per_1k"] = round(passive * per_1k, 1)
    if passive * per_1k > 25:
        rep.findings.append(Finding(0, "passive voice", "warn",
                                    f"{passive * per_1k:.1f} per 1000 words"))

    return rep


# --- LaTeX sources ---------------------------------------------------------
# The front matter is written in LaTeX, so none of the rules above ever saw it,
# and two em dashes lived on the copyright page of a book that hard-fails on
# them. LaTeX spells the em dash `---`, which is invisible to BANNED_CHARS.

TEX_COMMENT = re.compile(r"(?<!\\)%.*$", re.M)
TEX_MACRO = re.compile(r"\\[a-zA-Z@]+\*?")


def tex_prose(text: str) -> list[tuple[int, str]]:
    """Line-numbered prose from a .tex source, comments and macros removed."""
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        line = TEX_COMMENT.sub("", raw)
        if not line.strip():
            continue
        out.append((i, line))
    return out


def check_tex(path: Path) -> Report:
    rep = Report(path=path)
    for lineno, line in tex_prose(path.read_text(encoding="utf-8")):
        if "---" in line:
            rep.findings.append(
                Finding(lineno, "em dash", "fail", line.strip()[:100],
                        "`---` is the LaTeX em dash. Hard cut, same as in prose.")
            )
        for ch, name in BANNED_CHARS.items():
            if ch in line:
                rep.findings.append(
                    Finding(lineno, name, "fail", line.strip()[:100], "Hard cut."))
        flat = TEX_MACRO.sub(" ", line).replace("{", " ").replace("}", " ")
        for pattern, rule in BANNED_PHRASES:
            m = re.search(pattern, flat, re.I)
            if m:
                rep.findings.append(
                    Finding(lineno, rule, "fail", m.group(0), "Cut it."))
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", help=".qmd files to check")
    ap.add_argument("--all", action="store_true", help="check every chapter")
    ap.add_argument("--stats", action="store_true", help="print statistics even when clean")
    ap.add_argument("--warn-as-fail", action="store_true")
    args = ap.parse_args()

    targets: list[Path] = [Path(p) for p in args.paths]
    if args.all or not targets:
        targets = sorted(
            list((ROOT / "chapters").glob("*.qmd"))
            + list((ROOT / "frontmatter").glob("*.qmd"))
            + list((ROOT / "backmatter").glob("*.qmd"))
            + [ROOT / "index.qmd"]
        )
        # Generated reference pages are tables and addresses, not prose. Scoring
        # a list of 21 URLs for sentence rhythm produces noise, not findings.
        GENERATED = {"dataset-index.qmd", "error-index.qmd", "contents.qmd"}
        targets = [
            t for t in targets
            if t.exists() and "smoke" not in t.name and t.name not in GENERATED
        ] + sorted((ROOT / "tex").glob("*.tex"))

    total_fail = 0
    total_warn = 0
    for path in targets:
        rep = check_tex(path) if path.suffix == ".tex" else check_file(path)
        fails = rep.failures
        warns = [f for f in rep.findings if f.severity == "warn"]
        total_fail += len(fails)
        total_warn += len(warns)
        if fails or warns or args.stats:
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                rel = path
            print(f"\n{rel}")
            if args.stats and rep.stats:
                bits = "  ".join(f"{k}={v}" for k, v in rep.stats.items())
                print(f"    {bits}")
            for f in fails + warns:
                loc = f"{f.line}" if f.line else "-"
                mark = "FAIL" if f.severity == "fail" else "warn"
                print(f"    [{mark}] line {loc:>4}  {f.rule}: {f.excerpt}")
                if f.note:
                    print(f"                    {f.note}")

    print(f"\n{len(targets)} file(s): {total_fail} failures, {total_warn} warnings")
    if total_fail or (args.warn_as_fail and total_warn):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
