"""
LAAP — Rust Memory Backend
Optional Rust-accelerated memory engine. Falls back to pure Python.
"""

from __future__ import annotations
import logging, os, sys
from pathlib import Path

logger = logging.getLogger("laap.memory.rust")

_rust_available = False
RustTokenCounter = None
RustMemoryEngine = None
RustExperienceGraph = None
RustSessionManager = None

# Add Rust build output to path
_rust_paths = [
    # Development build (debug)
    Path(__file__).parent.parent.parent.parent / "core" / "target" / "debug",
    # Release build
    Path(__file__).parent.parent.parent.parent / "core" / "target" / "release",
    # Installed via pip
    Path(__file__).parent.parent.parent / "core",
]
for _p in _rust_paths:
    if _p.exists():
        sys.path.insert(0, str(_p))

# Try to import Rust native module
try:
    from laap_core import TokenCounter as RustTokenCounter
    from laap_core import MemoryEngine as RustMemoryEngine
    from laap_core import ExperienceGraph as RustExperienceGraph
    from laap_core import SessionManager as RustSessionManager
    _rust_available = True
    logger.info("Rust memory engine loaded (laap_core)")
except ImportError:
    logger.info("Rust core not available — using Python fallback")
except Exception as e:
    logger.warning("Rust core load failed: %s", e)


def rust_available() -> bool:
    return _rust_available


__all__ = [
    "rust_available",
    "RustTokenCounter",
    "RustMemoryEngine",
    "RustExperienceGraph",
    "RustSessionManager",
]
