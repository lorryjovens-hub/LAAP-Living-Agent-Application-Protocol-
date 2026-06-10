"""Quarantine Manager — 隔离机制"""
from __future__ import annotations
import time, json, logging, threading, uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("security.immune.quarantine")

@dataclass
class QuarantineItem:
    id: str = ""
    resource_id: str = ""
    reason: str = ""
    isolated_at: float = field(default_factory=time.time)
    release_at: Optional[float] = None
    status: str = "quarantined"
    observations: List[str] = field(default_factory=list)

class QuarantineManager:
    def __init__(self, default_duration: int = 3600):
        self.default_duration = default_duration
        self._items: Dict[str, QuarantineItem] = {}
        self._lock = threading.RLock()
    def quarantine(self, resource_id: str, reason: str, duration: Optional[int] = None) -> str:
        item = QuarantineItem(
            id=f"q_{uuid.uuid4().hex[:8]}",
            resource_id=resource_id,
            reason=reason,
            release_at=time.time() + (duration or self.default_duration)
        )
        with self._lock:
            self._items[item.id] = item
        logger.warning(f"Quarantined {resource_id}: {reason}")
        return item.id
    def release(self, item_id: str) -> bool:
        with self._lock:
            item = self._items.get(item_id)
            if item:
                item.status = "released"
                item.release_at = time.time()
                return True
            return False
    def is_quarantined(self, resource_id: str) -> bool:
        with self._lock:
            return any(i.resource_id == resource_id and i.status == "quarantined" for i in self._items.values())
    def get_active(self) -> List[QuarantineItem]:
        return [i for i in self._items.values() if i.status == "quarantined"]
    def auto_release(self) -> int:
        now = time.time()
        released = 0
        with self._lock:
            for item in list(self._items.values()):
                if item.status == "quarantined" and item.release_at and now >= item.release_at:
                    item.status = "released"
                    released += 1
        return released
