#!/usr/bin/env bash
# One-time toolchain setup for the No Lab Required build.
# Installs Quarto (userland, no sudo), TinyTeX, the book's Python env, and the fonts.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPT="$HOME/.local/opt"
BIN="$HOME/.local/bin"
QV="1.10.18"
mkdir -p "$OPT" "$BIN" "$ROOT/build-logs"

echo "### 1/5 Quarto $QV"
if [ ! -x "$OPT/quarto-$QV/bin/quarto" ]; then
  [ -f "/tmp/quarto-$QV.tar.gz" ] || curl -fsSL -o "/tmp/quarto-$QV.tar.gz" \
    "https://github.com/quarto-dev/quarto-cli/releases/download/v$QV/quarto-$QV-macos.tar.gz"
  rm -rf "$OPT/quarto-$QV" "$OPT/bin" "$OPT/share"
  mkdir -p "$OPT/quarto-$QV"
  tar -xzf "/tmp/quarto-$QV.tar.gz" -C "$OPT/quarto-$QV"
fi
ln -sf "$OPT/quarto-$QV/bin/quarto" "$BIN/quarto"
export PATH="$BIN:$PATH"
quarto --version

echo "### 2/5 Python env"
if [ ! -x "$ROOT/.venv/bin/python" ]; then
  /opt/homebrew/bin/python3 -m venv "$ROOT/.venv"
fi
"$ROOT/.venv/bin/python" -m pip install --quiet --upgrade pip wheel
"$ROOT/.venv/bin/python" -m pip install --quiet \
  biopython pandas numpy scipy matplotlib seaborn requests \
  jupyter nbformat nbclient ipykernel pyyaml statsmodels
"$ROOT/.venv/bin/python" -c "import Bio,pandas,numpy,scipy,matplotlib,seaborn,statsmodels; print('py ok', Bio.__version__, pandas.__version__)"

echo "### 3/5 TinyTeX"
quarto install tinytex --no-prompt --update-path || quarto install tinytex --no-prompt || true

echo "### 4/5 Fonts"
FDIR="$HOME/Library/Fonts"
mkdir -p "$FDIR" /tmp/nlrfonts
cd /tmp/nlrfonts
fetch_font () { # url  glob
  local url="$1" zipname; zipname="$(basename "$url")"
  [ -f "$zipname" ] || curl -fsSL -o "$zipname" "$url"
  unzip -oq "$zipname" -d "${zipname%.zip}" || true
}
fetch_font "https://github.com/adobe-fonts/source-serif/releases/download/4.005R/source-serif-4.005_Desktop.zip"
fetch_font "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
fetch_font "https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip"
# Desktop OTF/TTF only. Skip variable fonts and web formats — XeLaTeX wants static faces.
find /tmp/nlrfonts \( -name '*.ttf' -o -name '*.otf' \) \
  ! -path '*variable*' ! -path '*Variable*' ! -name '*VF.ttf' ! -name '*Italic-VF*' \
  ! -path '*web*' -print0 | while IFS= read -r -d '' f; do cp -n "$f" "$FDIR/" 2>/dev/null || true; done
cd "$ROOT"

echo "### 5/5 Verify fonts visible to XeLaTeX"
fc-cache -f "$FDIR" >/dev/null 2>&1 || true
fc-list | grep -icE "source serif 4|^.*Inter[-_ ]|JetBrains Mono" || true

echo "### TOOLCHAIN DONE"
