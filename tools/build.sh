#!/usr/bin/env bash
# Canonical build entry point. Everything the book needs to render, in one place,
# so that a fresh clone reproduces the published PDF byte-for-byte modulo dates.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# TinyTeX names its bin directory after the platform: universal-darwin on
# macOS, x86_64-linux or aarch64-linux elsewhere. Glob it rather than guess.
for d in "$HOME/Library/TinyTeX/bin"/* "$HOME/.TinyTeX/bin"/*; do
  [ -d "$d" ] && PATH="$d:$PATH"
done
export PATH="$HOME/.local/bin:$PATH"
export QUARTO_PYTHON="$ROOT/.venv/bin/python"
export NLR_TERMS_OUT="$ROOT/build-logs/terms.tsv"
export NLR_ERRORS_OUT="$ROOT/build-logs/errors.tsv"
export MPLBACKEND=Agg
# matplotlib caches the list of installed fonts. If the book's faces were
# installed after matplotlib last ran, that cache still says they do not exist
# and every figure silently falls back to DejaVu Sans.
rm -f "$("$ROOT/.venv/bin/python" -c 'import matplotlib; print(matplotlib.get_cachedir())')"/fontlist-*.json 2>/dev/null || true

mkdir -p build-logs
: > "$NLR_TERMS_OUT"
: > "$NLR_ERRORS_OUT"

# `fresh` throws away the execution cache first. Use it for a release build:
# with freeze:auto a chapter whose source did not change keeps its stored
# output, which is right during writing and wrong when a data file underneath
# it has moved.
if [ "${2:-}" = "fresh" ] || [ "${1:-}" = "fresh" ]; then
  rm -rf _freeze .quarto
  echo "cleared the execution cache; every chapter will re-run"
  [ "${1:-}" = "fresh" ] && set -- "${2:-all}"
fi

TARGET="${1:-all}"
case "$TARGET" in
  pdf)  quarto render --to pdf ;;
  html) quarto render --to html ;;
  all)  quarto render ;;
  *)    quarto render --to "$TARGET" ;;
esac
