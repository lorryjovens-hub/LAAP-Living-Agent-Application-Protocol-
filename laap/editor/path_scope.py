"""
LAAP — Path Scope Enforcer

Restrict file operations to allowed directories,
preventing path traversal and unauthorized access.
"""

from __future__ import annotations
import os, fnmatch, logging
from pathlib import Path
from typing import List, Optional, Set, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("laap.editor.path_scope")


@dataclass
class PathScopeConfig:
    """Configuration for path scope enforcement"""
    allowed_dirs: List[str] = field(default_factory=lambda: [
        os.getcwd(),
        os.path.expanduser("~"),
    ])
    blocked_patterns: List[str] = field(default_factory=lambda: [
        "*.pyc", "__pycache__/*", ".git/*", "node_modules/*",
        ".venv/*", "venv/*", "env/*", ".env",
        "*.so", "*.dll", "*.dylib",
    ])
    allow_symlink_escape: bool = False
    max_path_depth: int = 50
    follow_symlinks: bool = False


class PathScopeEnforcer:
    """Enforce path restrictions for file operations"""

    def __init__(self, config: Optional[PathScopeConfig] = None):
        self.config = config or PathScopeConfig()
        # Normalize allowed directories
        self._allowed: List[str] = []
        for d in self.config.allowed_dirs:
            abs_d = os.path.abspath(os.path.expanduser(d))
            if os.path.isdir(abs_d) or not os.path.exists(abs_d):
                self._allowed.append(abs_d)

    def check(self, path: str, operation: str = "read") -> Tuple[bool, str]:
        """Check if a path is allowed for the given operation.
        Returns (is_allowed, reason_if_blocked)."""
        try:
            abs_path = os.path.abspath(os.path.expanduser(path))
        except (ValueError, OSError) as e:
            return False, f"Invalid path: {e}"

        # Check path depth
        parts = abs_path.replace("\\", "/").split("/")
        if len(parts) > self.config.max_path_depth:
            return False, f"Path depth {len(parts)} exceeds maximum {self.config.max_path_depth}"

        # Check blocked patterns
        path_str = abs_path.replace("\\", "/")
        for pattern in self.config.blocked_patterns:
            if fnmatch.fnmatch(path_str, pattern) or \
               fnmatch.fnmatch(os.path.basename(path_str), pattern):
                return False, f"Path matches blocked pattern: {pattern}"

        # Check symlink escape
        if not self.config.follow_symlinks and os.path.islink(abs_path):
            target = os.readlink(abs_path)
            if not os.path.isabs(target):
                target = os.path.join(os.path.dirname(abs_path), target)
            target = os.path.abspath(target)
            if not self._is_in_allowed(target):
                if self.config.allow_symlink_escape:
                    return True, ""
                return False, f"Symlink target outside allowed directories: {target}"

        # Check allowed directories
        if not self._is_in_allowed(abs_path):
            return False, f"Path not in allowed directories: {abs_path}"

        return True, ""

    def _is_in_allowed(self, path: str) -> bool:
        """Check if path is within any allowed directory."""
        for allowed in self._allowed:
            try:
                common = os.path.commonpath([path, allowed])
                if common == allowed:
                    return True
            except ValueError:
                continue
        return False

    def restrict(self, path: str) -> str:
        """Return the path if allowed, otherwise raise PermissionError."""
        allowed, reason = self.check(path)
        if not allowed:
            raise PermissionError(reason)
        return path

    def add_allowed_dir(self, directory: str):
        """Add an additional allowed directory."""
        abs_dir = os.path.abspath(os.path.expanduser(directory))
        if abs_dir not in self._allowed:
            self._allowed.append(abs_dir)

    @property
    def status(self) -> dict:
        return {
            "allowed_dirs": self._allowed,
            "blocked_patterns": self.config.blocked_patterns,
            "follow_symlinks": self.config.follow_symlinks,
        }


# Global path scope enforcer
path_scope = PathScopeEnforcer()
