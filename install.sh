#!/usr/bin/env bash
# LAAP - Universal Installer (macOS / Linux / WSL)
# One command: $ laap  — after running this script and opening a new terminal.
#
# This installs LAAP from the current directory (editable mode), then
# symlinks bin/laap into ~/.local/bin/laap (which is normally in $PATH
# via the user-level PATH).
#
# Usage:
#   ./install.sh
#
# If you don't have ~/.local/bin in PATH, the script will print a hint.

set -e

LAAP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${LAAP_BIN_DIR:-$HOME/.local/bin}"
LAUNCHER="$LAAP_DIR/bin/laap"

echo "========================================"
echo "  LAAP - Universal Installer"
echo "========================================"
echo "  Source : $LAAP_DIR"
echo "  Bin dir: $BIN_DIR"
echo

# --- 1) Sanity checks -------------------------------------------------------
if [ ! -f "$LAUNCHER" ]; then
    echo "[LAAP] ERROR: $LAUNCHER not found. Run this from the LAAP project root."
    exit 1
fi
chmod +x "$LAUNCHER"

PY=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        PY="$cand"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "[LAAP] ERROR: Python 3 not found. Install Python 3.10+ from your package manager."
    exit 1
fi
PY_VERSION=$("$PY" -c "import sys; print('%d.%d' % sys.version_info[:2])")
echo "[LAAP] Using Python $PY_VERSION ($PY)"

# --- 2) pip install -e (editable, local source) -----------------------------
echo "[LAAP] Installing LAAP in editable mode..."
"$PY" -m pip install -e "$LAAP_DIR" -q
echo "  done."

# --- 3) Symlink the launcher into ~/.local/bin ------------------------------
mkdir -p "$BIN_DIR"
TARGET="$BIN_DIR/laap"
if [ -L "$TARGET" ] || [ -f "$TARGET" ]; then
    echo "[LAAP] Removing old launcher at $TARGET"
    rm -f "$TARGET"
fi
ln -s "$LAUNCHER" "$TARGET"
echo "[LAAP] Linked: $TARGET -> $LAUNCHER"

# --- 4) PATH hint -----------------------------------------------------------
case ":$PATH:" in
    *":$BIN_DIR:"*) echo "[LAAP] $BIN_DIR is already in PATH" ;;
    *)
        SHELL_NAME="$(basename "${SHELL:-$SHELL}")"
        RC_FILE="$HOME/.bashrc"
        case "$SHELL_NAME" in
            zsh)  RC_FILE="$HOME/.zshrc" ;;
            fish) RC_FILE="$HOME/.config/fish/config.fish" ;;
        esac
        echo
        echo "[LAAP] NOTE: $BIN_DIR is not currently in your PATH."
        echo "       To enable the 'laap' command in a new terminal, add this line to $RC_FILE:"
        echo
        echo "           export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo
        echo "       Then run:  source $RC_FILE"
        ;;
esac

echo
echo "========================================"
echo "  LAAP installed successfully!"
echo
echo "  Usage (in a new terminal):"
echo "    laap                  - launch TUI"
echo "    laap -i               - REPL mode"
echo "    laap -q \"question\"    - single query"
echo "    laap --version        - show version"
echo "    laap --help           - show all options"
echo "========================================"
