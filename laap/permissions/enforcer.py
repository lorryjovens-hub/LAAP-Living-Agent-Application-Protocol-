
"""LAAP — Permission System

Hierarchical permission system for tool access control.
Suppors allow/deny lists, user roles, and action confirmation.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class AccessLevel(Enum):
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"  # Ask user before executing
    RESTRICTED = "restricted"  # Execute with limitations


class PermissionLevel(Enum):
    """Permission levels for policy engine (used by policy.py)."""
    ALWAYS_ALLOW = "always_allow"
    ASK = "ask"
    ASK_TIMEOUT = "ask_timeout"
    DENY = "deny"
    RESTRICTED = "restricted"


class ResourceType(Enum):
    SHELL = "shell"
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"
    NETWORK = "network"
    CODE = "code"
    SYSTEM = "system"


@dataclass
class PermissionRule:
    """A single permission rule."""
    resource: str
    access: AccessLevel
    reason: str = ""
    max_args: Optional[Dict] = None  # e.g. {"path": "/tmp/*"} for path restrictions


@dataclass 
class PermissionContext:
    """Context for permission evaluation."""
    user_id: str = "default"
    session_id: str = ""
    platform: str = "cli"
    roles: Set[str] = field(default_factory=lambda: {"user"})
    safe_paths: Set[str] = field(default_factory=lambda: {os.path.expanduser("~"), "/tmp", os.getcwd()})


class PermissionEnforcer:
    """Central permission enforcement engine."""

    def __init__(self):
        self._rules: Dict[str, List[PermissionRule]] = {
            "shell": [PermissionRule("shell", AccessLevel.CONFIRM, "Shell commands need confirmation")],
            "file:write": [],
            "file:delete": [PermissionRule("file:delete", AccessLevel.CONFIRM, "File deletion needs confirmation")],
            "network": [],
        }
        self._context = PermissionContext()

    def set_context(self, ctx: PermissionContext):
        self._context = ctx

    def check(self, resource: str, args: Optional[Dict] = None) -> AccessLevel:
        """Check if an action is allowed."""
        rules = self._rules.get(resource, [])
        for rule in rules:
            if rule.access == AccessLevel.DENY:
                return AccessLevel.DENY
            if rule.access == AccessLevel.CONFIRM:
                return AccessLevel.CONFIRM
            if rule.access == AccessLevel.RESTRICTED:
                # Check arg restrictions
                if rule.max_args and args:
                    for k, pattern in rule.max_args.items():
                        val = args.get(k, "")
                        import fnmatch
                        if not fnmatch.fnmatch(str(val), pattern):
                            return AccessLevel.DENY
                return AccessLevel.RESTRICTED
        return AccessLevel.ALLOW

    def add_rule(self, resource: str, rule: PermissionRule):
        self._rules.setdefault(resource, []).append(rule)

    def allow_path(self, path: str):
        """Add a path to the safe paths list."""
        self._context.safe_paths.add(os.path.abspath(os.path.expanduser(path)))


# ---- Aliases for backward compatibility ----
# Used by agent/base.py which imports "enforcer" (lowercase)
enforcer = PermissionEnforcer
