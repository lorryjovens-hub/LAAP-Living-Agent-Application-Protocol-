#!/usr/bin/env python3
"""LAAP Comprehensive Installer — Python deps + optional Rust core"""

import subprocess, sys, os, shutil

VERSION = "0.3.0"
RUST_DIR = os.path.join(os.path.dirname(__file__), "core")

_G = "[38;5;214m"
_OK = "[38;5;82m"
_W = "[38;5;179m"
_RST = "[0m"
_B = "[1m"
_D = "[38;5;240m"


def step(msg): print(f"  {_G}◆{_RST} {msg}...")
def ok(msg): print(f"  {_OK}✓{_RST} {msg}")
def warn(msg): print(f"  {_W}⚠{_RST} {msg}")


def main():
    print(f"
  {_G}{_B}LAAP v{VERSION} — Installation{_RST}")
    print(f"  {_D}{"="*50}{_RST}
")

    step("Installing Python dependencies")
    pkgs = [
        "numpy>=1.24.0", "pydantic>=2.0.0",
        "httpx>=0.27.0", "docstring-parser>=0.15",
    ]
    for p in pkgs:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", p, "-q"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            warn(f"Failed to install {p}")

    # Optional extras
    extras = [
        ("OpenAI", ["openai>=1.0.0"]),
        ("Anthropic", ["anthropic>=0.30.0"]),
        ("API Server", ["fastapi>=0.104.0", "uvicorn>=0.24.0"]),
        ("Embeddings", ["sentence-transformers>=2.2.0"]),
        ("System Info", ["psutil>=5.9.0"]),
    ]
    for label, deps in extras:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"] + deps + ["-q"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            ok(f"{label}")
        except Exception:
            warn(f"{label} — optional, skipped")

    # Rust core
    if shutil.which("cargo"):
        step("Building Rust core")
        try:
            env = os.environ.copy()
            env["PYO3_USE_ABI3_FORWARD_COMPATIBILITY"] = "1"
            subprocess.check_call(
                ["cargo", "build", "--release"],
                cwd=RUST_DIR, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            ok("Rust core compiled")
        except Exception:
            warn("Rust build failed — Python fallback")
    else:
        warn("cargo not found — pure Python (install Rust for speed)")

    # Verify
    step("Verifying installation")
    try:
        import laap
        v = getattr(laap, "__version__", "?")
        ok(f"LAAP v{v} installed")
        from laap.llm.provider import Message, StreamEvent
        from laap.agent.base import Agent
        ok("Core modules OK")
    except Exception as e:
        warn(f"Verify: {e}")

    try:
        from laap.memory.rust_backend import rust_available
        if rust_available(): ok("Rust accelerator: ACTIVE")
    except ImportError:
        pass

    print(f"
  {_OK}{_B}LAAP v{VERSION} ready!{_RST}")
    print(f"  {_D}Run: python -m laap.api.cli{_RST}
")

if __name__ == "__main__":
    main()
