"""Policy Enforcer"""
from __future__ import annotations
import time, json, logging, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("security.policy.enforcer")

class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    AUDIT = "audit"
    CHALLENGE = "challenge"

@dataclass
class PolicyContext:
    action: str = ""
    resource: str = ""
    actor: str = ""
    attributes: Dict = field(default_factory=dict)

class PolicyEnforcer:
    def __init__(self):
        self._rules: List[Dict] = []
        self._lock = threading.RLock()
    def add_rule(self, action: str, resource: str, effect: str = "allow", conditions: Dict = None):
        with self._lock:
            self._rules.append({"action": action, "resource": resource, "effect": effect, "conditions": conditions or {}})
    def enforce(self, context: PolicyContext) -> PolicyDecision:
        for rule in self._rules:
            if rule["action"] in ("*", context.action) and rule["resource"] in ("*", context.resource):
                if rule["effect"] == "allow":
                    return PolicyDecision.ALLOW
                elif rule["effect"] == "deny":
                    return PolicyDecision.DENY
                elif rule["effect"] == "audit":
                    return PolicyDecision.AUDIT
        return PolicyDecision.DENY
