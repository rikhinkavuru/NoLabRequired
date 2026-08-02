#!/usr/bin/env bash
# Canonical build entry point. Everything the book needs to render, in one place,
# so that a fresh clone reproduces the published PDF byte-for-byte modulo dates.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PATH="$HOME/.local/bin:$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"
export QUARTO_PYTHON="$ROOT/.venv/bin/python"
export NLR_TERMS_OUT="$ROOT/build-logs/terms.tsv"
export NLR_ERRORS_OUT="$ROOT/build-logs/errors.tsv"
export MPLBACKEND=Agg

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
