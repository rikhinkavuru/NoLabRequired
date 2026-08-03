#!/usr/bin/env bash
# One-time toolchain setup for the No Lab Required build.
# Installs Quarto (userland, no sudo), TinyTeX, the book's Python env, and the fonts.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPT="$HOME/.local/opt"
BIN="$HOME/.local/bin"
QV="1.10.18"

case "$(uname -s)" in
  Darwin) QUARTO_ASSET="quarto-$QV-macos.tar.gz"; FONT_DIR="$HOME/Library/Fonts" ;;
  Linux)  case "$(uname -m)" in
            aarch64|arm64) QUARTO_ASSET="quarto-$QV-linux-arm64.tar.gz" ;;
            *)             QUARTO_ASSET="quarto-$QV-linux-amd64.tar.gz" ;;
          esac
          FONT_DIR="$HOME/.local/share/fonts" ;;
  *) echo "unsupported platform: $(uname -s)"; exit 1 ;;
esac
mkdir -p "$OPT" "$BIN" "$ROOT/build-logs"

echo "### 1/5 Quarto $QV"
if [ ! -x "$OPT/quarto-$QV/bin/quarto" ]; then
  [ -f "/tmp/$QUARTO_ASSET" ] || curl -fsSL -o "/tmp/$QUARTO_ASSET" \
    "https://github.com/quarto-dev/quarto-cli/releases/download/v$QV/$QUARTO_ASSET"
  rm -rf "$OPT/quarto-$QV" "$OPT/bin" "$OPT/share"
  mkdir -p "$OPT/quarto-$QV"
  tar -xzf "/tmp/$QUARTO_ASSET" -C "$OPT/quarto-$QV"
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
FDIR="$FONT_DIR"
mkdir -p "$FDIR" /tmp/nlrfonts
cd /tmp/nlrfonts
fetch_font () { # url  glob
  local url="$1" zipname; zipname="$(basename "$url")"
  [ -f "$zipname" ] || curl -fsSL -o "$zipname" "$url"
  unzip -oq "$zipname" -d "${zipname%.zip}" || true
}
# Charis, which is Matthew Carter's Charter extended by SIL, and Inconsolata,
# which Raph Levien drew for printed code listings. Both OFL.
fetch_font "https://github.com/silnrsi/font-charis/releases/download/v7.000/Charis-7.000.zip"
fetch_font "https://github.com/googlefonts/Inconsolata/releases/download/v3.000/fonts_otf.zip"
# Desktop OTF/TTF only. Skip variable fonts and web formats — XeLaTeX wants static faces.
# Only the widths and weights the book uses. Inconsolata ships every width from
# UltraCondensed to UltraExpanded and copying all of them makes font selection
# ambiguous.
for f in $(find /tmp/nlrfonts -name 'Charis-Regular.ttf' -o -name 'Charis-Italic.ttf' \
                              -o -name 'Charis-Bold.ttf' -o -name 'Charis-BoldItalic.ttf' \
                              -o -name 'Inconsolata-Regular.otf' -o -name 'Inconsolata-Bold.otf'); do
  cp -f "$f" "$FDIR/" 2>/dev/null || true
done
cd "$ROOT"

echo "### 5/5 Verify fonts visible to XeLaTeX"
fc-cache -f "$FDIR" >/dev/null 2>&1 || true
fc-list : family | tr "," "\n" | grep -icE "^Charis$|^Inconsolata$" || true

echo "### TOOLCHAIN DONE"
