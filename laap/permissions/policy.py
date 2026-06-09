"""LAAP — Policy Engine

Policy-based permission rules with YAML configuration support.
"""

from __future__ import annotations
import json, logging, os, re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Pattern
from pathlib import Path

from laap.permissions.enforcer import PermissionLevel

logger = logging.getLogger("laap.permissions.policy")


@dataclass
class PolicyRule:
    """A single policy rule"""
    resource_pattern: str
    level: PermissionLevel
    description: str = ""
    max_count: Optional[int] = None
    expires_at: Optional[float] = None

    def matches(self, resource: str) -> bool:
        try:
            return bool(re.match(self.resource_pattern, resource))
        except re.error:
            return resource == self.resource_pattern


class PolicyEngine:
    """Policy engine for permission rules"""

    def __init__(self):
        self._rules: List[PolicyRule] = []
        self._load_defaults()

    def _load_defaults(self):
        defaults = [
            PolicyRule(r"env:read", PermissionLevel.ALWAYS_ALLOW, "Read environment variables"),
            PolicyRule(r"file:read", PermissionLevel.ALWAYS_ALLOW, "Read files"),
            PolicyRule(r"shell:execute", PermissionLevel.ASK, "Execute shell commands"),
            PolicyRule(r"file:write", PermissionLevel.ASK, "Write files"),
            PolicyRule(r"file:delete", PermissionLevel.ASK_TIMEOUT, "Delete files"),
            PolicyRule(r"git:push", PermissionLevel.ASK, "Push to git"),
            PolicyRule(r"network:.*", PermissionLevel.ASK_TIMEOUT, "Network operations"),
        ]
        self._rules.extend(defaults)

    def add_rule(self, rule: PolicyRule):
        self._rules.append(rule)

    def evaluate(self, resource: str) -> Optional[PolicyRule]:
        for rule in self._rules:
            if rule.matches(resource):
                return rule
        return None

    def load_file(self, path: str):
        p = Path(path)
        if not p.exists():
            return
        try:
            import yaml
            with open(p) as f:
                data = yaml.safe_load(f)
            for entry in data.get("rules", []):
                self._rules.append(PolicyRule(
                    resource_pattern=entry["pattern"],
                    level=PermissionLevel(entry["level"]),
                    description=entry.get("description", ""),
                ))
        except Exception as e:
            logger.error(f"Failed to load policy file {path}: {e}")

    def to_dict(self) -> dict:
        return {
            "rules": [
                {"pattern": r.resource_pattern, "level": r.level.value,
                 "description": r.description}
                for r in self._rules
            ]
        }
