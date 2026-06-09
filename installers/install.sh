#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# LAAP one-liner installer — universal Unix (macOS, Linux, WSL, *BSD)
# ----------------------------------------------------------------------------
# Usage:
#   curl -LsSf https://laap.dev/install.sh | bash
#
# Strategy (in order):
#   1. uv  (fast, isolated venv, recommended)
#   2. pipx (if already installed)
#   3. pip --user (last resort)
#
# All paths land in ~/.local/bin; the script ensures that directory is on PATH.
# ----------------------------------------------------------------------------

set -euo pipefail

C_RESET=""; C_GOLD=""; C_BOLD=""; C_DIM=""; C_RED=""; C_GREEN=""
if [[ -t 1 ]]; then
    C_RESET=$'\033[0m'; C_GOLD=$'\033[38;5;220m'; C_BOLD=$'\033[1m'
    C_DIM=$'\033[2m';    C_RED=$'\033[31m';          C_GREEN=$'\033[32m'
fi
info()    { printf "%b[laap]%b %s\n" "$C_GOLD" "$C_RESET" "$*"; }
success() { printf "%b[laap]%b %s\n" "$C_GREEN" "$C_RESET" "$*"; }
warn()    { printf "%b[laap]%b %s\n" "$C_RED" "$C_RESET" "$*" >&2; }

# Pretty banner
printf "%b%s%b" "$C_GOLD$C_BOLD" "$(cat <<'EOF'
  _      _____    _    ____   ____
 | |    |  __ \  | |  / __ \ / __ \
 | |    | |__) | | | | |  | | |  | |
 | |    |  ___/  | | | |  | | |  | |
 | |____| |      | | | |__| | |__| |
 |______|_|      |_|  \____/ \____/

EOF
)" "$C_RESET"

# ---- Detect Python --------------------------------------------------------
PYTHON=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        ver=$("$cand" -c "import sys; print('%d.%d' % sys.version_info[:2])")
        if [[ "${ver%.*}" -ge 3 ]] && [[ "${ver#*.}" -ge 10 ]]; then
            PYTHON="$cand"
            break
        fi
    fi
done
if [[ -z "$PYTHON" ]]; then
    warn "Python 3.10+ is required but was not found on PATH."
    warn "Install Python from https://python.org or via your package manager."
    exit 1
fi
info "Python: $("$PYTHON" --version)"

# ---- 1) uv path -----------------------------------------------------------
if command -v uv >/dev/null 2>&1; then
    info "uv detected, delegating to install-uv.sh"
    exec bash "$(dirname "$0")/install-uv.sh" "$@"
fi

# ---- 2) pipx path ---------------------------------------------------------
if command -v pipx >/dev/null 2>&1; then
    info "pipx detected, using pipx install laap"
    pipx install laap
    pipx ensurepath || true
    success "laap installed via pipx."
    exit 0
fi

# ---- 3) pip --user fallback ----------------------------------------------
PIP_CMD=""
for cand in pip3 pip; do
    if command -v "$cand" >/dev/null 2>&1; then
        PIP_CMD="$cand"
        break
    fi
done
if [[ -z "$PIP_CMD" ]]; then
    warn "No pip, pipx, or uv found. Bootstrapping pip..."
    "$PYTHON" -m ensurepip --upgrade || {
        warn "ensurepip failed. Install pip from https://pip.pypa.io/en/stable/installation/"
        exit 1
    }
    PIP_CMD="$PYTHON -m pip"
fi

info "Installing laap via $PIP_CMD install --user ..."
"$PIP_CMD" install --user --upgrade laap

# Ensure ~/.local/bin on PATH
LOCAL_BIN="$HOME/.local/bin"
case ":$PATH:" in
    *":$LOCAL_BIN:"*) ;;
    *)
        SHELL_RC="$HOME/.bashrc"
        [[ -n "${ZSH_VERSION:-}" ]] && SHELL_RC="$HOME/.zshrc"
        if [[ -f "$SHELL_RC" ]] && ! grep -q '\.local/bin' "$SHELL_RC"; then
            {
                echo ""
                echo "# Added by LAAP installer"
                echo 'export PATH="$HOME/.local/bin:$PATH"'
            } >> "$SHELL_RC"
            success "Added ~/.local/bin to PATH in $SHELL_RC"
        else
            success "Add ~/.local/bin to your PATH and restart the shell."
        fi
        ;;
esac

# Verify
if command -v laap >/dev/null 2>&1; then
    success "laap installed: $(laap --version 2>&1 | head -n 1)"
else
    success "Installation complete. Open a new terminal and type 'laap'."
fi
