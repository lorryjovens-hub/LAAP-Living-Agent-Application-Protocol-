"""LAAP — Audit Logging System

Records all security-relevant events: tool execution, file access,
permission decisions, and configuration changes.
"""

from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

logger = logging.getLogger("laap.audit")


@dataclass
class AuditEvent:
    timestamp: float = field(default_factory=time.time)
    event_type: str = ""        # tool_exec, file_read, auth, config
    actor: str = "agent"        # who performed the action
    action: str = ""            # what was done
    resource: str = ""          # what was affected
    result: str = ""            # allowed, denied, error
    details: Dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """Centralized audit logging for security events."""

    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._events: list = []

    def log(self, event_type: str, action: str, resource: str,
            result: str = "allowed", actor: str = "agent",
            details: Optional[Dict] = None):
        if not self._enabled:
            return
        event = AuditEvent(
            event_type=event_type, actor=actor, action=action,
            resource=resource, result=result, details=details or {},
        )
        self._events.append(event)
        logger.info(f"AUDIT [{result}] {actor}:{action} on {resource}")

    def get_recent(self, limit: int = 50) -> list:
        return [asdict(e) for e in self._events[-limit:]]

    def get_by_type(self, event_type: str, limit: int = 50) -> list:
        return [asdict(e) for e in self._events if e.event_type == event_type][-limit:]


# Singleton
_audit = None
def get_audit_logger() -> AuditLogger:
    global _audit
    if _audit is None:
        _audit = AuditLogger()
    return _audit
