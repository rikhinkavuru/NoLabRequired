#!/usr/bin/env bash
# The gate. Everything that has to be true before this book ships.
# Exits non-zero on the first failure, so it is safe to wire to a release step.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"
PDF="_book/bioinformatics-workbook-v1.0.pdf"

pass=0; fail=0
run () {  # run <name> <command...>
  printf '\n=== %s ===\n' "$1"; shift
  if "$@"; then pass=$((pass+1)); else fail=$((fail+1)); printf '  ^^ FAILED\n'; fi
}

run "prose"                 "$PY" tools/check_prose.py --all
run "content and structure" "$PY" tools/check_content.py
run "cross-references"      "$PY" tools/check_crossrefs.py
run "sequences are real"    "$PY" tools/check_sequences.py
run "quoted errors"         "$PY" tools/check_errors.py
run "referenced files exist" "$PY" tools/check_data_refs.py
run "figures have alt text" "$PY" tools/check_figures.py
run "translation proof"     "$PY" tools/verify_translation.py

if [ ! -f "$PDF" ]; then
  printf '\n=== build ===\n'
  bash tools/build.sh all || { printf '  ^^ BUILD FAILED\n'; fail=$((fail+1)); }
fi

run "layout and delivery"   "$PY" tools/check_layout.py "$PDF"
run "page budgets"          "$PY" tools/check_pages.py "$PDF"
run "links resolve"         "$PY" tools/check_links.py

printf '\n========================================\n'
printf '  %d check group(s) passed, %d failed\n' "$pass" "$fail"
printf '========================================\n'
[ "$fail" -eq 0 ] || exit 1

printf '\nStill required before this is publishable:\n'
[ -f backmatter/glossary.qmd ] || printf '  - the glossary has not been written\n'
[ -d answers ] && [ "$(ls -A answers 2>/dev/null | wc -l | tr -d ' ')" -gt 0 ] \
  || printf '  - the exercise answers have not been written\n'
printf '  - independent technical review (stated as a gap in the acknowledgments)\n'
