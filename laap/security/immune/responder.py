"""Immune Responder — 自动响应系统"""
from __future__ import annotations
import time, json, logging, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from laap.security.immune.detector import ThreatEvent, ThreatLevel

logger = logging.getLogger("security.immune.responder")

class ResponseAction(str, Enum):
    LOG = "log"
    ALERT = "alert"
    BLOCK = "block"
    ISOLATE = "isolate"
    QUARANTINE = "quarantine"
    SHUTDOWN = "shutdown"
    EVOLVE = "evolve"

@dataclass
class Incident:
    id: str = ""
    threat_id: str = ""
    action_taken: ResponseAction = ResponseAction.LOG
    status: str = "open"
    resolved_at: Optional[float] = None
    notes: str = ""

class ImmuneResponder:
    def __init__(self):
        self._response_map: Dict[str, ResponseAction] = {
            "info": ResponseAction.LOG,
            "low": ResponseAction.LOG,
            "medium": ResponseAction.ALERT,
            "high": ResponseAction.BLOCK,
            "critical": ResponseAction.ISOLATE,
        }
        self._incidents: List[Incident] = []
        self._lock = threading.RLock()
    def respond(self, threat: ThreatEvent) -> Incident:
        action = self._response_map.get(threat.level.value, ResponseAction.LOG)
        incident = Incident(id=f"inc_{int(time.time()*1e6)}", threat_id=threat.id, action_taken=action)
        logger.info(f"Responding to {threat.id}: {action.value}")
        if action in (ResponseAction.BLOCK, ResponseAction.ISOLATE, ResponseAction.QUARANTINE):
            self._execute_action(action, threat)
        with self._lock:
            self._incidents.append(incident)
        return incident
    def _execute_action(self, action: ResponseAction, threat: ThreatEvent):
        logger.warning(f"Executing {action.value} for threat: {threat.description}")
    def resolve(self, incident_id: str, notes: str = ""):
        with self._lock:
            for inc in self._incidents:
                if inc.id == incident_id:
                    inc.status = "resolved"
                    inc.resolved_at = time.time()
                    inc.notes = notes
    def get_active(self) -> List[Incident]:
        return [i for i in self._incidents if i.status == "open"]
