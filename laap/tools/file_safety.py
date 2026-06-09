"""
LAAP — File Safety Module (ported from Hermes Agent)

Provides safe file read/write/delete operations with:
- Path traversal protection (prevent escapes from allowed directories)
- Symbolic link safety checks
- File size limits for reads
- Binary file detection
- Backup creation before overwrites
"""

from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Optional, Set, Tuple, List

logger = logging.getLogger("laap.tools.file_safety")

# ── Defaults ─────────────────────────────────────────────────────

_DEFAULT_MAX_READ_SIZE = 100 * 1024  # 100KB
_DEFAULT_MAX_WRITE_SIZE = 10 * 1024 * 1024  # 10MB
_DEFAULT_ALLOWED_DIRS: Set[Path] = set()

# Binary file extensions (skip content operations)
_BINARY_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp",
    ".mp3", ".mp4", ".wav", ".ogg", ".flac", ".mov", ".avi",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".pyc", ".pyo", ".pyd",
    ".db", ".sqlite", ".sqlite3",
    ".ttf", ".otf", ".woff", ".woff2",
    ".o", ".a", ".lib",
    ".whl", ".egg", ".egg-info",
}


def is_binary_path(path: Path) -> bool:
    """Check if a file path has a binary extension."""
    return path.suffix.lower() in _BINARY_EXTENSIONS


def is_binary_content(data: bytes, sample_size: int = 8192) -> bool:
    """Detect binary content by checking for null bytes in a sample."""
    sample = data[:sample_size]
    return b"\0" in sample


def set_allowed_directories(dirs: List[Path]):
    """Set the list of allowed directories for file operations."""
    global _DEFAULT_ALLOWED_DIRS
    _DEFAULT_ALLOWED_DIRS = set(dirs)


def add_allowed_directory(d: Path):
    """Add a directory to the allowed list."""
    _DEFAULT_ALLOWED_DIRS.add(d.resolve())


# ── Path Safety ──────────────────────────────────────────────────

def resolve_safe_path(path: str | Path,
                      allowed_dirs: Optional[Set[Path]] = None) -> Tuple[Path, str]:
    """Resolve a path and validate it's within allowed directories.

    Args:
        path: Path to resolve (can be relative or absolute)
        allowed_dirs: Set of allowed base directories (defaults to global)

    Returns:
        Tuple of (resolved Path, error message)
        On success: (Path, "")
        On failure: (None, error_description)
    """
    dirs = allowed_dirs if allowed_dirs is not None else _DEFAULT_ALLOWED_DIRS
    try:
        p = Path(path).resolve()
    except (OSError, RuntimeError) as e:
        return None, f"Path resolution error: {e}"

    # Symlink safety: ensure the resolved path is not a symlink to outside
    if p.is_symlink():
        try:
            target = p.readlink()
            if not target.is_absolute():
                target = (p.parent / target).resolve()
            if dirs and not any(
                str(target).startswith(str(d)) for d in dirs
            ):
                return None, f"Symlink target outside allowed dirs: {target}"
        except (OSError, RuntimeError) as e:
            return None, f"Symlink check error: {e}"

    # Path traversal check
    if dirs:
        str_path = str(p)
        if not any(str_path.startswith(str(d)) for d in dirs):
            return None, f"Path outside allowed directories: {p}"

    return p, ""


def safe_read(path: str | Path, max_size: int = _DEFAULT_MAX_READ_SIZE,
              allowed_dirs: Optional[Set[Path]] = None,
              encoding: str = "utf-8") -> Tuple[Optional[str], str]:
    """Safely read a file with size limits and binary detection.

    Args:
        path: File path
        max_size: Maximum bytes to read
        allowed_dirs: Allowed base directories
        encoding: Text encoding

    Returns:
        Tuple of (content, error_message)
    """
    resolved, error = resolve_safe_path(path, allowed_dirs)
    if error:
        return None, error

    if not resolved.exists():
        return None, f"File not found: {resolved}"
    if not resolved.is_file():
        return None, f"Not a file: {resolved}"

    # Check if binary
    if is_binary_path(resolved):
        return None, f"Binary file: {resolved.name}"

    # Check file size before reading
    try:
        file_size = resolved.stat().st_size
    except OSError as e:
        return None, f"Cannot read file stats: {e}"

    if file_size > max_size:
        return None, f"File too large: {file_size:,} bytes (max {max_size:,})"

    # Read and verify content
    try:
        data = resolved.read_bytes()
    except OSError as e:
        return None, f"Cannot read file: {e}"

    if is_binary_content(data):
        return None, f"Binary content detected in: {resolved.name}"

    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        return None, f"Cannot decode {encoding}: {resolved.name}"

    return text, ""


def safe_write(path: str | Path, content: str,
               allowed_dirs: Optional[Set[Path]] = None,
               max_size: int = _DEFAULT_MAX_WRITE_SIZE,
               create_backup: bool = True,
               encoding: str = "utf-8") -> Tuple[bool, str]:
    """Safely write content to a file.

    Args:
        path: File path
        content: Text content to write
        allowed_dirs: Allowed base directories
        max_size: Maximum content size
        create_backup: Create .bak before overwriting
        encoding: Text encoding

    Returns:
        Tuple of (success, message)
    """
    resolved, error = resolve_safe_path(path, allowed_dirs)
    if error:
        return False, error

    # Check content size
    data = content.encode(encoding)
    if len(data) > max_size:
        return False, f"Content too large: {len(data):,} bytes (max {max_size:,})"

    # Create parent directories
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return False, f"Cannot create directory: {e}"

    # Backup existing file
    if create_backup and resolved.exists():
        backup_path = resolved.with_suffix(resolved.suffix + ".bak")
        try:
            import shutil
            shutil.copy2(str(resolved), str(backup_path))
        except OSError as e:
            logger.warning(f"Backup failed for {resolved}: {e}")

    # Write
    try:
        resolved.write_text(content, encoding=encoding)
        return True, f"Written {len(data):,} bytes to {resolved}"
    except OSError as e:
        return False, f"Write error: {e}"


def safe_delete(path: str | Path,
                allowed_dirs: Optional[Set[Path]] = None,
                trash: bool = True) -> Tuple[bool, str]:
    """Safely delete a file.

    Args:
        path: File path
        allowed_dirs: Allowed base directories
        trash: Move to trash instead of permanent delete

    Returns:
        Tuple of (success, message)
    """
    resolved, error = resolve_safe_path(path, allowed_dirs)
    if error:
        return False, error

    if not resolved.exists():
        return False, f"Not found: {resolved}"

    if not resolved.is_file():
        return False, f"Not a file: {resolved}"

    try:
        if trash:
            # Simple rename-based trash
            trash_dir = resolved.parent / ".trash"
            trash_dir.mkdir(exist_ok=True)
            import shutil
            shutil.move(str(resolved), str(trash_dir / resolved.name))
            return True, f"Moved to trash: {resolved.name}"
        else:
            resolved.unlink()
            return True, f"Deleted: {resolved}"
    except OSError as e:
        return False, f"Delete error: {e}"
