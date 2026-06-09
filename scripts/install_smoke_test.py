#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAAP fresh-install smoke test.

Simulates what a brand-new user experiences when installing LAAP from
scratch on Windows, macOS, or Linux. Runs entirely locally; the only
network operations are pulling the uv / pip / npm packages.

Usage examples
--------------
    # 1) Just inspect the current environment (no install, no mutation)
    python scripts/install_smoke_test.py

    # 2) Run the full installer (default channel = uv, if uv is on PATH)
    python scripts/install_smoke_test.py --install

    # 3) Simulate a brand-new user: uninstall → install → verify → cleanup
    python scripts/install_smoke_test.py --install --clean

    # 4) Test the npm channel only
    python scripts/install_smoke_test.py --channel npm --install

    # 5) Force a specific channel even if uv/npm are missing
    python scripts/install_smoke_test.py --channel pip --install

What "verify" means
-------------------
    1. `laap` resolves on PATH
    2. `laap --version` exits 0 and prints a non-empty string
    3. `laap -i` shows the Hermes-style welcome banner
       (we capture 4s of output and grep for "LAAP Agent" / "Available Tools")

Exit codes
----------
    0   all checks passed
    1   a check failed
    2   prerequisites missing (e.g. no Python, no network)
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# ----------------------------------------------------------------------
# ANSI helpers (graceful on dumb terminals)
# ----------------------------------------------------------------------
_IS_TTY = sys.stdout.isatty()


def _ansi(code: str) -> str:
    return code if _IS_TTY else ""


GOLD = _ansi("\033[38;5;220m")
BOLD = _ansi("\033[1m")
DIM = _ansi("\033[2m")
RED = _ansi("\033[31m")
GREEN = _ansi("\033[32m")
YELLOW = _ansi("\033[33m")
RESET = _ansi("\033[0m")


def info(msg: str) -> None:
    print(f"{GOLD}[smoke]{RESET} {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"{GREEN}[  ok ]{RESET} {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"{YELLOW}[ warn]{RESET} {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"{RED}[ FAIL]{RESET} {msg}", flush=True)


def step(msg: str) -> None:
    print(f"\n{BOLD}{GOLD}━━━ {msg} ━━━{RESET}", flush=True)


# ----------------------------------------------------------------------
# Platform detection
# ----------------------------------------------------------------------
IS_WINDOWS = platform.system().lower() == "windows"
IS_MAC = platform.system().lower() == "darwin"
IS_LINUX = platform.system().lower() == "linux"
IS_UNIX = not IS_WINDOWS

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLER_DIR = REPO_ROOT / "installers"
SCRIPTS_DIR = REPO_ROOT / "scripts"


# ----------------------------------------------------------------------
# Result container
# ----------------------------------------------------------------------
@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""

    def render(self) -> str:
        badge = f"{GREEN}PASS{RESET}" if self.passed else f"{RED}FAIL{RESET}"
        return f"  {badge}  {self.name}" + (f"  {DIM}— {self.detail}{RESET}" if self.detail else "")


# ----------------------------------------------------------------------
# Subprocess helpers
# ----------------------------------------------------------------------
def run(
    cmd: List[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
    timeout: float = 600,
    input_text: Optional[str] = None,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """Run a subprocess with sensible defaults for cross-platform output."""
    if env is None:
        env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUNBUFFERED", "1")
    if IS_WINDOWS:
        # Avoid Windows opening a new console window
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    else:
        creationflags = 0
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        input=input_text,
        check=check,
        creationflags=creationflags,
    )


def stream(cmd: List[str], *, cwd: Optional[Path] = None,
           env: Optional[dict] = None, timeout: float = 600,
           input_text: Optional[str] = None) -> subprocess.Popen:
    """Spawn a subprocess and stream its output to the parent stdout.

    Returns the Popen; caller is responsible for wait / kill."""
    if env is None:
        env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if IS_WINDOWS:
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    else:
        creationflags = 0
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )


def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def detect_python() -> Optional[str]:
    for cand in (["python3", "python"] if IS_UNIX else ["python3", "python", "py"]):
        p = which(cand)
        if not p:
            continue
        try:
            r = run([p, "-c", "import sys; v=sys.version_info; print('%d.%d' % (v[0], v[1]))"])
        except Exception:
            continue
        ver = r.stdout.strip()
        try:
            maj, mn = (int(x) for x in ver.split("."))
        except ValueError:
            continue
        if maj == 3 and mn >= 10:
            return p
    return None


# ----------------------------------------------------------------------
# Channel detection
# ----------------------------------------------------------------------
CHANNELS = ["uv", "pipx", "npm", "pip", "local"]

# Priority order used by the installer's own chain (uv -> pipx -> pip)
_AUTO_PRIORITY = ["uv", "pipx", "pip"]


def detect_channel(forced: Optional[str]) -> str:
    if forced:
        if forced not in CHANNELS:
            raise SystemExit(f"unknown channel: {forced}; valid: {CHANNELS}")
        return forced
    # Auto: pick the first channel that has the required tool.
    for ch in _AUTO_PRIORITY:
        if ch == "uv"   and which("uv"):   return "uv"
        if ch == "pipx" and which("pipx"): return "pipx"
        if ch == "pip":
            # any pip works
            for cand in ("pip3", "pip", "python3 -m pip"):
                if cand == "python3 -m pip":
                    py = detect_python()
                    if py and run([py, "-m", "pip", "--version"]).returncode == 0:
                        return "pip"
                elif which(cand):
                    return "pip"
    if which("npm") and which("node"):
        return "npm"
    return "local"


# ----------------------------------------------------------------------
# Banner capture
# ----------------------------------------------------------------------
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")


def capture_banner() -> CheckResult:
    """Run `laap -i`, capture 4s of output, kill it, and check for the banner."""
    proc = stream(["laap", "-i"])
    try:
        time.sleep(4.0)
        # Send /exit to gracefully terminate
        try:
            proc.stdin.write("/exit\n")  # type: ignore[union-attr]
            proc.stdin.flush()
        except Exception:
            pass
        time.sleep(1.0)
    finally:
        try: proc.kill()
        except Exception: pass
    out, _ = proc.communicate(timeout=5)
    stripped = ANSI_ESCAPE.sub("", out)
    # Heuristics: look for known banner elements
    has_logo   = "LAAP" in stripped and ("Agent" in stripped or "__" in stripped)
    has_tools  = "Available Tools" in stripped
    has_skills = "Available Skills" in stripped or "21 tools" in stripped
    if has_logo and (has_tools or has_skills):
        return CheckResult("Hermes-style banner rendered", True,
                           f"({len(stripped)} chars captured)")
    return CheckResult("Hermes-style banner rendered", False,
                       f"missing elements: logo={has_logo} tools={has_tools} skills={has_skills}")


# ----------------------------------------------------------------------
# Channel-specific install / verify
# ----------------------------------------------------------------------
def uninstall_uv() -> None:
    if which("uv") is None:
        return
    info("Uninstalling previous laap via uv...")
    run(["uv", "tool", "uninstall", "laap"], check=False)


def install_uv() -> None:
    info("Running install-uv script (uv tool install)...")
    if IS_WINDOWS:
        ps = INSTALLER_DIR / "install-uv.ps1"
        if not ps.exists():
            raise FileNotFoundError(f"missing installer: {ps}")
        # Use a clean child PowerShell that does NOT inherit user PATH for
        # isolation. We just pass through, since uv reads its own config.
        p = stream(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps)])
        out, _ = p.communicate(timeout=300)
        if p.returncode != 0:
            raise RuntimeError(f"install-uv.ps1 exited {p.returncode}\n{out}")
    else:
        sh = INSTALLER_DIR / "install-uv.sh"
        if not sh.exists():
            raise FileNotFoundError(f"missing installer: {sh}")
        # Set env overrides
        env = os.environ.copy()
        env.setdefault("LAAP_VERSION", "0.3.0")
        p = stream(["bash", str(sh)], env=env)
        out, _ = p.communicate(timeout=300)
        if p.returncode != 0:
            raise RuntimeError(f"install-uv.sh exited {p.returncode}\n{out}")


def uninstall_pipx() -> None:
    if which("pipx"):
        run(["pipx", "uninstall", "laap"], check=False)


def install_pipx() -> None:
    run(["pipx", "install", "laap"], check=True, timeout=300)


def install_pip() -> None:
    py = detect_python()
    if not py:
        raise RuntimeError("no Python 3.10+ interpreter found")
    # --user puts laap.exe in %APPDATA%\Python\Scripts (Windows) or
    # ~/.local/bin (Unix), both of which are typically on PATH.
    run([py, "-m", "pip", "install", "--user", "--upgrade", "laap"],
        check=True, timeout=600)


def uninstall_pip() -> None:
    py = detect_python()
    if py:
        run([py, "-m", "pip", "uninstall", "-y", "laap"], check=False)


def install_npm() -> None:
    if not which("npm"):
        raise RuntimeError("npm not found; install Node.js 16+ first")
    if IS_WINDOWS:
        cmd = ["npm", "install", "-g", "laap-ai"]
    else:
        cmd = ["npm", "install", "-g", "laap-ai"]
    run(cmd, check=True, timeout=600)


def uninstall_npm() -> None:
    if which("npm"):
        run(["npm", "uninstall", "-g", "laap-ai"], check=False)


def install_local() -> None:
    """Install the local source tree via `pip install -e` (used as last resort)."""
    py = detect_python()
    if not py:
        raise RuntimeError("no Python 3.10+ interpreter found")
    run([py, "-m", "pip", "install", "-e", str(REPO_ROOT), "[cli]"],
        check=True, timeout=900)


def uninstall_local() -> None:
    py = detect_python()
    if py:
        run([py, "-m", "pip", "uninstall", "-y", "laap"], check=False)


# ----------------------------------------------------------------------
# Verification routines
# ----------------------------------------------------------------------
def verify_resolve() -> CheckResult:
    p = which("laap")
    if p:
        return CheckResult("`laap` resolves on PATH", True, f"-> {p}")
    return CheckResult("`laap` resolves on PATH", False, "not found")


def verify_version() -> CheckResult:
    p = which("laap")
    if not p:
        return CheckResult("`laap --version`", False, "not on PATH")
    try:
        r = run([p, "--version"], timeout=30)
    except subprocess.TimeoutExpired:
        return CheckResult("`laap --version`", False, "timed out after 30s")
    if r.returncode == 0 and r.stdout.strip():
        return CheckResult("`laap --version`", True, r.stdout.strip().splitlines()[0][:80])
    return CheckResult("`laap --version`", False, f"exit={r.returncode}, no output")


def verify_banner() -> CheckResult:
    if not which("laap"):
        return CheckResult("Hermes-style banner", False, "not on PATH")
    return capture_banner()


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def banner() -> None:
    art = r"""
   __         _____ ___    _    _____   _   _ _____ ____    _____ ___  _   _
   \ \       / ____|__ \  | |  | ____| | \ | | ____|  _ \  |_   _/ _ \| \ | |
    \ \  /\ / / _   __) | | |  |  _|   |  \| |  _| | |_) |   | || | | |  \| |
     \ \/  v / | | |__ <  | |  | |___  | |\  | |___|  _ <    | || |_| | |\  |
      \  /\ /  | | ___) | | |__|_____| | | \_|_____|_| \_\  | | \___/| | \_|
       \/  \/   |_||____/ |_____|     |_| (_)_____(_)  (_) |_|     |_| (_)
    """
    print(f"{GOLD}{BOLD}{art}{RESET}")
    print(f"  {BOLD}LAAP fresh-install smoke test{RESET}")
    print(f"  {DIM}Platform: {platform.system()} {platform.release()} ({platform.machine()}){RESET}")
    print(f"  {DIM}Python:   {sys.version.split()[0]}{RESET}")
    print(f"  {DIM}Repo:     {REPO_ROOT}{RESET}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--install", action="store_true",
                    help="actually run the installer (default: only check current state)")
    ap.add_argument("--clean",   action="store_true",
                    help="with --install: uninstall any pre-existing laap first")
    ap.add_argument("--channel", choices=CHANNELS,
                    help="force a specific install channel (default: auto-detect)")
    ap.add_argument("--skip-banner", action="store_true",
                    help="don't capture the Hermes banner (skip the slow check)")
    ap.add_argument("--no-cleanup", action="store_true",
                    help="leave the install in place after the test")
    args = ap.parse_args()

    banner()

    # ---- Step 0: preflight ----
    step("Preflight")
    py = detect_python()
    if not py:
        fail("Python 3.10+ not found on PATH")
        return 2
    ok(f"Python: {py}  ({run([py, '--version']).stdout.strip()})")
    ok(f"Repo root: {REPO_ROOT}")
    if IS_WINDOWS:
        ok(f"Shell: Windows PowerShell / CMD")
    else:
        ok(f"Shell: {os.environ.get('SHELL', '/bin/sh')}")

    channel = detect_channel(args.channel)
    info(f"Install channel: {channel}")

    # ---- Step 1: pre-state ----
    step("Before install")
    pre_resolve  = verify_resolve()
    pre_version  = verify_version()
    pre_banner   = verify_banner() if not args.skip_banner else None
    for r in (pre_resolve, pre_version, pre_banner):
        if r: print(r.render())

    # ---- Step 2: install ----
    if args.install:
        step("Install")
        # Optional cleanup first
        if args.clean:
            info("--clean requested; uninstalling existing laap (best-effort)...")
            for fn in (uninstall_uv, uninstall_pipx, uninstall_pip, uninstall_npm, uninstall_local):
                try: fn()
                except Exception as e: warn(f"  cleanup step failed: {e}")

        # Run the channel-specific installer
        try:
            installer = {
                "uv":    install_uv,
                "pipx":  install_pipx,
                "pip":   install_pip,
                "npm":   install_npm,
                "local": install_local,
            }[channel]
            installer()
            ok(f"install via {channel} succeeded")
        except Exception as e:
            fail(f"install via {channel} failed: {e}")
            return 1

        # Some installers (uv on Windows) only add ~/.local/bin to user PATH
        # in HKCU\Environment, which the CURRENT process can't see without
        # a fresh login. For verification, fall back to the absolute path
        # reported by `uv tool dir` if `laap` isn't on PATH yet.
        if not which("laap") and channel == "uv" and which("uv"):
            tool_dir = run(["uv", "tool", "dir"]).stdout.strip()
            bin_dir = Path(tool_dir)
            candidate = bin_dir / ("laap.exe" if IS_WINDOWS else "laap")
            if candidate.exists():
                info(f"`laap` not on PATH yet (new-terminal required) — also at {candidate}")

    # ---- Step 3: post-state ----
    step("After install")
    post_resolve = verify_resolve()
    post_version = verify_version()
    post_banner  = verify_banner() if not args.skip_banner else None
    results = [post_resolve, post_version]
    if post_banner: results.append(post_banner)
    for r in results:
        print(r.render())

    # ---- Step 4: verdict ----
    step("Verdict")
    # If we were asked NOT to install, treat pre-state as the verdict
    if not args.install:
        info("--install not given; reporting pre-state as the verdict")
        targets = [pre_resolve, pre_version] + ([pre_banner] if pre_banner else [])
    else:
        targets = [post_resolve, post_version] + ([post_banner] if post_banner else [])

    passed = sum(1 for r in targets if r.passed)
    total  = len(targets)
    if passed == total:
        ok(f"All {total} checks passed")
        verdict = 0
    else:
        fail(f"{total - passed}/{total} checks failed")
        verdict = 1

    # ---- Step 5: optional cleanup ----
    if args.install and args.clean and not args.no_cleanup:
        step("Cleanup")
        info("Removing the install we just made (--clean + not --no-cleanup)")
        for fn in (uninstall_uv, uninstall_pipx, uninstall_pip, uninstall_npm, uninstall_local):
            try: fn()
            except Exception as e: warn(f"  cleanup step failed: {e}")
        ok("cleanup done")

    print()
    return verdict


if __name__ == "__main__":
    sys.exit(main())
