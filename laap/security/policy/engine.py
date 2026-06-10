"""Policy Evaluation Engine"""
from __future__ import annotations
import time, json, logging, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("security.policy.engine")

class Effect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE = "require"

@dataclass
class PolicyRule:
    id: str = ""
    name: str = ""
    effect: Effect = Effect.ALLOW
    conditions: List[Dict] = field(default_factory=list)
    priority: int = 0

class PolicyEngine:
    def __init__(self):
        self._rules: List[PolicyRule] = []
        self._lock = threading.RLock()
    def add_rule(self, rule: PolicyRule):
        with self._lock:
            self._rules.append(rule)
            self._rules.sort(key=lambda r: -r.priority)
    def evaluate(self, action: str, context: Dict) -> Effect:
        for rule in self._rules:
            if self._match_conditions(rule.conditions, context):
                return rule.effect
        return Effect.DENY
    def _match_conditions(self, conditions: List[Dict], context: Dict) -> bool:
        for cond in conditions:
            key = cond.get("key", "")
            operator = cond.get("op", "eq")
            value = cond.get("value")
            actual = context.get(key)
            if operator == "eq" and actual != value: return False
            if operator == "neq" and actual == value: return False
            if operator == "in" and actual not in value: return False
        return True
