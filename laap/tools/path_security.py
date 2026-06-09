"""
LAAP — Path Security (ported from Hermes Agent)

Validates and sanitizes file paths to prevent path traversal attacks.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Set


def is_path_traversal(path: str | Path) -> bool:
    """Check if a path attempts directory traversal.

    Detects patterns like ../, ..\\, absolute paths when relative expected.
    """
    p = str(path)
    # Check for parent directory traversal
    if ".." in p.split("/") or ".." in p.split("\\"):
        return True
    # Check for encoded traversal
    if "%2e%2e" in p.lower() or "%252e" in p.lower():
        return True
    return False


def sanitize_path_component(component: str) -> str:
    """Sanitize a single path component (filename or directory name).

    Removes or replaces characters that could be used for traversal or
    shell injection.
    """
    # Remove path separators
    sanitized = component.replace("/", "_").replace("\\", "_").replace(":", "_")
    # Remove null bytes
    sanitized = sanitized.replace("\0", "")
    # Remove other dangerous characters
    for ch in ["<", ">", "|", "*", "?"]:
        sanitized = sanitized.replace(ch, "_")
    return sanitized


def resolve_safe(root: str | Path, user_path: str) -> Optional[Path]:
    """Resolve a user-provided path relative to a root, safely.

    Args:
        root: The allowed root directory
        user_path: User-provided path (may be absolute or relative)

    Returns:
        Resolved Path if safe, None if traversal detected
    """
    root_path = Path(root).resolve()
    combined = root_path / user_path
    resolved = combined.resolve()

    # Ensure the resolved path is within the root
    try:
        resolved.relative_to(root_path)
        return resolved
    except ValueError:
        return None


def is_hidden(path: str | Path) -> bool:
    """Check if a file or directory is hidden."""
    p = Path(path)
    return p.name.startswith(".")


def is_safe_extension(extension: str, allowed: Optional[Set[str]] = None,
                      blocked: Optional[Set[str]] = None) -> bool:
    """Check if a file extension is safe for operations.

    Args:
        extension: File extension (e.g., '.py')
        allowed: Set of allowed extensions (if None, all are allowed)
        blocked: Set of blocked extensions (default: executable/sensitive)

    Returns:
        True if safe
    """
    ext = extension.lower().lstrip(".")

    if blocked is None:
        blocked = {"exe", "dll", "so", "dylib", "bin", "com", "msi",
                    "bat", "cmd", "ps1", "sh", "vbs", "js", "scr"}

    if ext in blocked:
        return False
    if allowed is not None and ext not in allowed:
        return False
    return True
