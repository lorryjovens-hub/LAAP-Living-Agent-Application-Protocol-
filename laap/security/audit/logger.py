"""Audit Logger — Immutable audit trail"""
from __future__ import annotations
import time, json, hashlib, logging, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("security.audit.logger")

class AuditCategory(str, Enum):
    AUTH = "auth"
    ACCESS = "access"
    CHANGE = "change"
    EVOLUTION = "evolution"
    SECURITY = "security"
    SYSTEM = "system"

@dataclass
class AuditEvent:
    id: str = ""
    category: AuditCategory = AuditCategory.SYSTEM
    action: str = ""
    actor: str = ""
    resource: str = ""
    details: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    hash: str = ""
    previous_hash: str = ""

class AuditLogger:
    def __init__(self):
        self._events: List[AuditEvent] = []
        self._lock = threading.RLock()
    def log(self, category: AuditCategory, action: str, actor: str, resource: str = "", details: Dict = None) -> str:
        prev_hash = self._events[-1].hash if self._events else "0" * 64
        event = AuditEvent(
            id=f"aud_{int(time.time()*1e6)}_{hashlib.md5((action+actor+str(time.time())).encode()).hexdigest()[:8]}",
            category=category, action=action, actor=actor, resource=resource,
            details=details or {}, previous_hash=prev_hash
        )
        chain_data = f"{prev_hash}:{event.id}:{event.action}:{event.actor}:{event.timestamp}"
        event.hash = hashlib.sha256(chain_data.encode()).hexdigest()
        with self._lock:
            self._events.append(event)
        logger.info(f"Audit: {category.value} | {action} | {actor}")
        return event.id
    def verify_chain(self) -> bool:
        with self._lock:
            prev_hash = "0" * 64
            for event in self._events:
                chain_data = f"{prev_hash}:{event.id}:{event.action}:{event.actor}:{event.timestamp}"
                expected = hashlib.sha256(chain_data.encode()).hexdigest()
                if event.hash != expected:
                    return False
                prev_hash = event.hash
            return True
    def query(self, category: Optional[AuditCategory] = None, actor: str = "", limit: int = 100) -> List[AuditEvent]:
        results = self._events
        if category:
            results = [e for e in results if e.category == category]
        if actor:
            results = [e for e in results if e.actor == actor]
        return results[-limit:]
