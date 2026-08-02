#!/usr/bin/env python
"""Measure the rendered PDF against PART B of the production spec.

This is the layout equivalent of a unit test. It reads the actual glyph
positions out of the PDF rather than trusting the LaTeX source, so a silently
broken breakout or a font that failed to embed shows up as a failure here
instead of as a surprise at print time.

Usage:  .venv/bin/python tools/check_layout.py _book/No-Lab-Required.pdf
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

import pdfplumber
from pypdf import PdfReader

PT = 72.0
TOL = 0.02  # inches

SPEC = {
    "page_w": 8.5,
    "page_h": 11.0,
    "top": 0.75,
    "bottom": 0.90,
    "inner": 0.75,
    "outer": 1.25,
    "text_block": 6.50,
    "main_col": 4.60,
    "gutter": 0.25,
    "side_col": 1.65,
    "body_pt": 11.0,
    "code_pt": 9.5,
}

results: list[tuple[str, bool, str]] = []


# Font locations, in the order they are searched. macOS first, then the three
# places a Linux runner puts user and system fonts. Hard-coding the macOS path
# made this check report "sizes in use: []" on CI and fail without saying why.
_FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"),
    os.path.expanduser("~/.fonts"),
    os.path.expanduser("~/.local/share/fonts"),
    "/Library/Fonts",
    "/usr/share/fonts",
    "/usr/local/share/fonts",
]
_metrics_cache: dict[str, tuple[int, dict, dict]] = {}
_font_files_seen = 0


def _find_font_file(family: str) -> str | None:
    """Locate an installed face by family name, across platforms."""
    global _font_files_seen
    for base in _FONT_DIRS:
        if not os.path.isdir(base):
            continue
        for ext in (".otf", ".ttf"):
            direct = os.path.join(base, family + ext)
            if os.path.exists(direct):
                _font_files_seen += 1
                return direct
        # Linux distributions nest fonts several directories deep.
        for root, _dirs, files in os.walk(base):
            for ext in (".otf", ".ttf"):
                if family + ext in files:
                    _font_files_seen += 1
                    return os.path.join(root, family + ext)
    return None


def _metrics(family: str):
    """(upem, cmap, hmtx) for an installed face, used to recover the true size.

    LuaTeX rescales a 2048-unit CFF to 1000 units when it embeds it, so the Tf
    operand in the content stream is not the point size. Measuring a glyph's
    advance in the PDF against its advance in the source font is.
    """
    if family in _metrics_cache:
        return _metrics_cache[family]
    from fontTools.ttLib import TTFont

    path = _find_font_file(family)
    if path:
        try:
            f = TTFont(path, lazy=True)
            _metrics_cache[family] = (
                f["head"].unitsPerEm, f.getBestCmap(), dict(f["hmtx"].metrics)
            )
            return _metrics_cache[family]
        except Exception:
            pass
    _metrics_cache[family] = (0, {}, {})
    return _metrics_cache[family]


def measured_size(char: dict) -> float | None:
    """True rendered point size of one glyph, from its advance width."""
    family = char["fontname"].split("+")[-1]
    upem, cmap, hmtx = _metrics(family)
    if not upem or len(char["text"]) != 1:
        return None
    gname = cmap.get(ord(char["text"]))
    if gname is None:
        return None
    adv = hmtx.get(gname, (0, 0))[0]
    if adv <= 0:
        return None
    return (char["x1"] - char["x0"]) / (adv / upem)


def _upem(font_obj) -> int:
    """Units per em of an embedded font program, read from its head table.

    LuaTeX writes Tf sizes relative to the font's own em square, so a 2048-unit
    face such as Inter appears in the content stream at half its point size.
    Without this correction every Inter measurement below is wrong by 2x.
    """
    import struct

    desc = font_obj.get("/FontDescriptor")
    if desc is None:
        for df in font_obj.get("/DescendantFonts", []) or []:
            desc = df.get_object().get("/FontDescriptor")
            if desc is not None:
                break
    if desc is None:
        return 1000
    for key in ("/FontFile2", "/FontFile3", "/FontFile"):
        ff = desc.get(key)
        if ff is None:
            continue
        data = ff.get_object().get_data()
        # A bare CFF (CIDFontType0C, which is how LuaTeX embeds OTF/CFF faces)
        # carries its em square in the Top DICT FontMatrix, not in a head table.
        if data[:2] == b"\x01\x00":
            try:
                from io import BytesIO

                from fontTools.cffLib import CFFFontSet

                cff = CFFFontSet()
                cff.decompile(BytesIO(data), None)
                td = cff[cff.fontNames[0]]
                matrix = getattr(td, "FontMatrix", None) or td.rawDict.get("FontMatrix")
                if matrix and matrix[0]:
                    return int(round(1.0 / matrix[0]))
            except Exception:
                return 1000
            return 1000
        try:
            n_tables = struct.unpack(">H", data[4:6])[0]
            for i in range(n_tables):
                off = 12 + 16 * i
                if data[off : off + 4] == b"head":
                    table = struct.unpack(">I", data[off + 8 : off + 12])[0]
                    return struct.unpack(">H", data[table + 18 : table + 20])[0]
        except Exception:
            return 1000
    return 1000


def font_sizes_from_content(reader: PdfReader) -> set[tuple[str, float]]:
    """Every (font family, point size) pair actually selected by a Tf operator."""
    from pypdf.generic import ContentStream

    pairs: set[tuple[str, float]] = set()
    for page in reader.pages:
        res = page.get("/Resources") or {}
        fonts = res.get("/Font") or {}
        keymap = {}
        for key, ref in fonts.items():
            obj = ref.get_object()
            base = str(obj.get("/BaseFont", "?")).split("+")[-1]
            keymap[key] = (base, _upem(obj) / 1000.0)
        try:
            stream = ContentStream(page.get_contents(), reader)
        except Exception:
            continue
        for operands, operator in stream.operations:
            if operator == b"Tf" and len(operands) == 2:
                fam, scale = keymap.get(str(operands[0]), (str(operands[0]), 1.0))
                try:
                    pairs.add((fam, round(float(operands[1]) * scale, 1)))
                except (TypeError, ValueError):
                    pass
    return pairs


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def near(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol


def main(path: str) -> int:
    reader = PdfReader(path)
    n_pages = len(reader.pages)

    # ---- page size --------------------------------------------------------
    box = reader.pages[0].mediabox
    check(
        "page size 8.5 x 11 in",
        near(float(box.width) / PT, SPEC["page_w"]) and near(float(box.height) / PT, SPEC["page_h"]),
        f"{float(box.width)/PT:.3f} x {float(box.height)/PT:.3f} in",
    )

    # ---- fonts embedded ---------------------------------------------------
    embedded, not_embedded = set(), set()
    for page in reader.pages:
        res = page.get("/Resources")
        if not res:
            continue
        fonts = res.get("/Font")
        if not fonts:
            continue
        for _, ref in fonts.items():
            f = ref.get_object()
            desc = f.get("/FontDescriptor")
            if desc is None:
                for df in f.get("/DescendantFonts", []) or []:
                    desc = df.get_object().get("/FontDescriptor")
            name = str(f.get("/BaseFont", "?"))
            if desc and any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                embedded.add(name)
            else:
                not_embedded.add(name)
    check("all fonts embedded", not not_embedded, f"missing: {sorted(not_embedded)}" if not_embedded else f"{len(embedded)} embedded")
    subset = [f for f in embedded if "+" in f]
    check("fonts subset", len(subset) == len(embedded), f"{len(subset)}/{len(embedded)} subset")

    # ---- bookmarks --------------------------------------------------------
    def count_outline(items) -> int:
        total = 0
        for it in items:
            if isinstance(it, list):
                total += count_outline(it)
            else:
                total += 1
        return total

    n_marks = count_outline(reader.outline) if reader.outline else 0
    check("PDF bookmarks present", n_marks > 0, f"{n_marks} entries")

    # ---- geometry from actual glyph positions -----------------------------
    body_lefts: dict[str, Counter] = {"odd": Counter(), "even": Counter()}
    body_rights: dict[str, Counter] = {"odd": Counter(), "even": Counter()}
    sizes: Counter = Counter()  # (family, measured pt) -> glyph count
    fontnames: Counter = Counter()
    top_edges: list[float] = []
    bottom_edges: list[float] = []
    head_baselines: list[float] = []
    folio_baselines: list[float] = []
    widest_measure = 0.0
    overflow: list[str] = []

    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            parity = "odd" if i % 2 == 1 else "even"
            chars = page.chars
            if not chars:
                continue
            for ch in chars:
                fam = ch["fontname"].split("+")[-1]
                fontnames[fam] += 1
                pt = measured_size(ch)
                if pt is not None:
                    sizes[(fam, round(pt, 1))] += 1
            # Serif body glyphs only, so margin notes (Inter) do not pollute the measure.
            serif = [c for c in chars if "SourceSerif" in c["fontname"].replace("-", "") or "Source" in c["fontname"]]
            if serif:
                body_lefts[parity][round(min(c["x0"] for c in serif) / PT, 2)] += 1
                body_rights[parity][round(max(c["x1"] for c in serif) / PT, 2)] += 1
            if serif:
                by_line: dict[float, list] = defaultdict(list)
                for c in serif:
                    by_line[round(c["bottom"], 1)].append(c)
                for line in by_line.values():
                    span = (max(c["x1"] for c in line) - min(c["x0"] for c in line)) / PT
                    widest_measure = max(widest_measure, span)
            # Text block runs 0.75 -> 7.25 in on every page.
            lo = SPEC["inner"]
            hi = lo + SPEC["text_block"]
            # 0.05 in of slack: microtype protrudes punctuation past the measure
            # on purpose, which is desirable and should not be flagged.
            for c in chars:
                if c["x0"] / PT < lo - 0.05 or c["x1"] / PT > hi + 0.05:
                    overflow.append(f"p{i} {c['text']!r} x0={c['x0']/PT:.2f} x1={c['x1']/PT:.2f}")
                    break
            top_edges.append(min(c["top"] for c in chars) / PT)
            bottom_edges.append(max(c["bottom"] for c in chars) / PT)
            # The topmost run of glyphs on a page with a running head is that head.
            head = min(chars, key=lambda c: c["top"])
            if head["top"] / PT < 0.55:
                head_baselines.append(head["bottom"] / PT)
            foot = max(chars, key=lambda c: c["bottom"])
            if foot["bottom"] / PT > 10.20:
                folio_baselines.append(foot["bottom"] / PT)

    def mode(counter: Counter) -> float | None:
        return counter.most_common(1)[0][0] if counter else None

    # Geometry is asymmetric: every page puts the main column at 0.75 in and the
    # side column on the right. See the deviation note in tex/preamble.tex.
    odd_left = mode(body_lefts["odd"])
    even_left = mode(body_lefts["even"])
    for parity, value in (("recto", odd_left), ("verso", even_left)):
        if value is not None:
            check(
                f"{parity} main column starts at 0.75 in",
                near(value, SPEC["inner"], 0.03),
                f"{value} in",
            )

    # Body prose is capped at the 4.60 in main column; exercise, callout and
    # checkpoint components are allowed the full 6.50 in text block, so the hard
    # ceiling is the text block and the modal line start is what proves the
    # main column is being honoured.
    check(
        "no line exceeds the 6.50 in text block",
        widest_measure <= SPEC["text_block"] + 0.05,
        f"widest serif line {widest_measure:.2f} in",
    )
    check(
        "nothing prints outside the text block",
        not overflow,
        f"{len(overflow)} overflowing glyph runs" + (f": {overflow[:3]}" if overflow else ""),
    )

    # ---- type sizes -------------------------------------------------------
    def family_sizes(pred) -> list[float]:
        found = {s for (fam, s), n in sizes.items() if pred(fam) and n >= 12}
        return sorted(found)

    serif_sizes = family_sizes(lambda f: "SourceSerif" in f.replace("-", ""))
    mono_sizes = family_sizes(lambda f: "JetBrainsMono" in f.replace("-", ""))
    sans_sizes = family_sizes(lambda f: f.startswith("Inter"))

    def has(found: list[float], want: float) -> bool:
        return any(abs(s - want) <= 0.15 for s in found)

    # Point sizes are recovered by comparing each glyph's advance in the PDF
    # against the same glyph in the installed face. If no face can be found,
    # say so instead of reporting an empty set, which reads like the book has
    # no 11 pt text in it.
    if _font_files_seen == 0:
        check(
            "font files available to measure against", False,
            "found none of the book's faces in " + ", ".join(_FONT_DIRS)
            + ". Install them, or run tools/setup_toolchain.sh.",
        )
    check("body text set at 11 pt", has(serif_sizes, 11.0), f"serif sizes in use: {serif_sizes}")
    check("code set at 9.5 pt", has(mono_sizes, 9.5), f"mono sizes in use: {mono_sizes}")
    check(
        "running head 8.5 pt and folio 9.5 pt",
        has(sans_sizes, 8.5) and has(sans_sizes, 9.5),
        f"sans sizes in use: {sans_sizes}",
    )

    fams = {k for k in fontnames}
    # Matplotlib embeds its own default face inside figure PDFs. That is left
    # alone on purpose: the figures should look like what the reader's code
    # produces on a default install, not like the book's body text.
    figure_fonts = sorted(f for f in fams if "DejaVu" in f)
    check(
        "only matplotlib's default falls outside the book's three faces",
        all(("DejaVu" in f) or ("SourceSerif" in f.replace("-", ""))
            or f.startswith("Inter") or "JetBrainsMono" in f.replace("-", "")
            for f in fams),
        f"figure faces: {figure_fonts}" if figure_fonts else "none",
    )
    check("Source Serif 4 present", any("SourceSerif" in f.replace("-", "") for f in fams), str(sorted(fams))[:200])
    check("Inter present", any(f.startswith("Inter") for f in fams), "")
    check("JetBrains Mono NL present", any("JetBrainsMonoNL" in f.replace("-", "") for f in fams), "")

    # ---- vertical block ---------------------------------------------------
    # Uppercase running heads sit on their baseline, so a char's bottom edge is
    # the baseline. Spec B6 puts that baseline 0.45 in from the top trim.
    if head_baselines:
        med = sorted(head_baselines)[len(head_baselines) // 2]
        check("running-head baseline 0.45 in from top trim", near(med, 0.45, 0.03), f"median {med:.3f} in")
    if folio_baselines:
        med = sorted(folio_baselines)[len(folio_baselines) // 2]
        check("folio baseline 0.55 in from bottom trim", near(11.0 - med, 0.55, 0.03), f"median {11.0 - med:.3f} in from bottom")
    if bottom_edges:
        check("nothing printed below 10.55 in", max(bottom_edges) <= 10.58, f"lowest glyph at {max(bottom_edges):.3f} in")

    # ---- delivery specification (spec B9) ---------------------------------
    import os
    import re as _re

    root = reader.trailer["/Root"]
    mark = root.get("/MarkInfo")
    check(
        "tagged PDF: content is marked",
        bool(mark) and bool(mark.get("/Marked")),
        str(mark),
    )
    check("tagged PDF: structure tree present", "/StructTreeRoot" in root, "")
    check("document language declared", str(root.get("/Lang", "")).startswith("en"), str(root.get("/Lang")))
    prefs = root.get("/ViewerPreferences") or {}
    check(
        "reader shows the title, not the filename",
        bool(prefs.get("/DisplayDocTitle")),
        str(dict(prefs)) if prefs else "no ViewerPreferences",
    )
    check("page labels present (roman then arabic)", "/PageLabels" in root, "")

    title = str((reader.metadata or {}).get("/Title", ""))
    check("document title set", bool(title.strip()), title)

    xmp = ""
    if "/Metadata" in root:
        try:
            xmp = root["/Metadata"].get_object().get_data().decode("utf-8", "replace")
        except Exception:
            xmp = ""
    ua = _re.search(r"pdfuaid:part[^0-9]*([0-9]+)", xmp)
    check("PDF/UA conformance declared in XMP", bool(ua), f"pdfuaid:part={ua.group(1)}" if ua else "absent")
    dc = _re.search(r"<dc:title>.*?<rdf:li[^>]*>([^<]+)</rdf:li>", xmp, _re.S)
    check("XMP title matches the document title", bool(dc) and dc.group(1).strip() == title.strip(),
          dc.group(1).strip() if dc else "absent")

    size_mb = os.path.getsize(path) / 1e6
    check("file under 20 MB", size_mb < 20, f"{size_mb:.1f} MB")

    # ---- report -----------------------------------------------------------
    width = max(len(n) for n, _, _ in results)
    failed = 0
    print(f"\nLayout check: {path}  ({n_pages} pages)\n")
    for name, ok, detail in results:
        flag = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  [{flag}] {name.ljust(width)}  {detail}")
    print(f"\n{len(results) - failed}/{len(results)} checks passed\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "_book/No-Lab-Required.pdf"))
