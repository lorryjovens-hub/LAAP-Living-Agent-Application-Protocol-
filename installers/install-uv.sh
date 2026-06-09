#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# LAAP one-liner installer — uv-based (Unix: macOS, Linux, WSL, *BSD)
# ----------------------------------------------------------------------------
# Usage:
#   curl -LsSf https://laap.dev/install-uv.sh | bash
#   curl -LsSf https://raw.githubusercontent.com/laap-agi/laap/main/installers/install-uv.sh | bash
#
# What it does:
#   1. Detect / install uv (the fast Python package manager)
#   2. Run `uv tool install laap` — creates an isolated venv, drops a
#      `laap` shim into ~/.local/bin
#   3. Make sure ~/.local/bin is on PATH for future shells
#
# Environment overrides:
#   LAAP_VERSION   specific version to install (default: latest)
#   LAAP_EXTRAS    extras to install, e.g. "tui" or "all" (default: empty)
#   LAAP_FROM      install from git/url instead of PyPI (advanced)
# ----------------------------------------------------------------------------

set -euo pipefail

# ---- Pretty logging helpers ----------------------------------------------
if [[ -t 1 ]]; then
    C_RESET=$'\033[0m'
    C_GOLD=$'\033[38;5;220m'
    C_BOLD=$'\033[1m'
    C_DIM=$'\033[2m'
    C_RED=$'\033[31m'
    C_GREEN=$'\033[32m'
else
    C_RESET=""; C_GOLD=""; C_BOLD=""; C_DIM=""; C_RED=""; C_GREEN=""
fi
info()    { printf "%b[laap]%b %s\n" "$C_GOLD" "$C_RESET" "$*"; }
success() { printf "%b[laap]%b %s\n" "$C_GREEN" "$C_RESET" "$*"; }
warn()    { printf "%b[laap]%b %s\n" "$C_RED" "$C_RESET" "$*" >&2; }

LAAP_BANNER="$(cat <<'EOF'
  _      _____    _    ____   ____
 | |    |  __ \  | |  / __ \ / __ \
 | |    | |__) | | | | |  | | |  | |
 | |    |  ___/  | | | |  | | |  | |
 | |____| |      | | | |__| | |__| |
 |______|_|      |_|  \____/ \____/

EOF
)"
printf "%b%s%b" "$C_GOLD$C_BOLD" "$LAAP_BANNER" "$C_RESET"

# ---- Step 1: ensure uv is installed --------------------------------------
if ! command -v uv >/dev/null 2>&1; then
    info "uv not found. Installing uv via the official installer..."
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        warn "Neither curl nor wget is available. Install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
    # astral installer drops uv into ~/.local/bin (or ~/.cargo/bin)
    if [[ -f "$HOME/.local/bin/env" ]]; then
        # shellcheck disable=SC1091
        source "$HOME/.local/bin/env"
    fi
    if ! command -v uv >/dev/null 2>&1; then
        warn "uv still not on PATH. Add ~/.local/bin to PATH and re-run."
        exit 1
    fi
    success "uv $(uv --version) installed."
else
    info "uv found: $(uv --version)"
fi

# ---- Step 2: install laap ------------------------------------------------
TARGET="laap"
EXTRA_ARGS=()
if [[ -n "${LAAP_FROM:-}" ]]; then
    TARGET="$LAAP_FROM"
elif [[ -n "${LAAP_VERSION:-}" ]]; then
    TARGET="laap==${LAAP_VERSION}"
fi
if [[ -n "${LAAP_EXTRAS:-}" ]]; then
    EXTRA_ARGS+=(--with "$LAAP_EXTRAS")
fi

info "Installing ${TARGET} via uv tool (isolated venv)..."
# shellcheck disable=SC2086
uv tool install --upgrade "${EXTRA_ARGS[@]}" "$TARGET"

# ---- Step 3: ensure ~/.local/bin is on PATH -------------------------------
LOCAL_BIN="$HOME/.local/bin"
PATH_LINE=""
case ":$PATH:" in
    *":$LOCAL_BIN:"*) ;; # already there
    *)
        if [[ -n "${BASH_VERSION:-}" ]]; then
            PATH_LINE="export PATH=\"\$HOME/.local/bin:\$PATH\""
        elif [[ -n "${ZSH_VERSION:-}" ]]; then
            PATH_LINE="export PATH=\"\$HOME/.local/bin:\$PATH\""
        fi
        ;;
esac

if [[ -n "$PATH_LINE" ]]; then
    SHELL_RC=""
    if [[ -n "${ZSH_VERSION:-}" ]]; then SHELL_RC="$HOME/.zshrc"
    elif [[ -n "${BASH_VERSION:-}" ]]; then SHELL_RC="$HOME/.bashrc"
    fi
    if [[ -n "$SHELL_RC" ]] && [[ -f "$SHELL_RC" ]] && ! grep -q '\.local/bin' "$SHELL_RC"; then
        {
            echo ""
            echo "# Added by LAAP installer"
            echo "$PATH_LINE"
        } >> "$SHELL_RC"
        success "Added ~/.local/bin to PATH in $SHELL_RC (restart shell to apply)."
    else
        success "Please add ~/.local/bin to your PATH and restart your shell."
    fi
fi

# ---- Verify --------------------------------------------------------------
if command -v laap >/dev/null 2>&1; then
    success "laap installed: $(laap --version 2>&1 | head -n 1)"
    echo ""
    printf "%bTry it:%b\n" "$C_BOLD" "$C_RESET"
    printf "    %blaap --version%b     # show version\n" "$C_GOLD" "$C_RESET"
    printf "    %blaap -i%b            # interactive REPL\n" "$C_GOLD" "$C_RESET"
    printf "    %blaap -q \"hi\"%b     # one-shot question\n" "$C_GOLD" "$C_RESET"
    printf "    %blaap%b               # full-screen TUI (in a real terminal)\n" "$C_GOLD" "$C_RESET"
else
    success "Installation complete. Open a new terminal and type 'laap'."
fi
