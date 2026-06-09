"""
LAAP — Event Bus

Publish/subscribe event system for decoupled communication between components.
"""

from __future__ import annotations
import logging, time, threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

logger = logging.getLogger("laap.events")


class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """A single event in the system"""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    priority: EventPriority = EventPriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"evt_{int(self.timestamp * 1000000)}"


EventHandler = Callable[[Event], None]


class EventBus:
    """Publish/subscribe event bus"""

    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._history: List[Event] = []
        self._max_history = 1000

    def subscribe(self, event_type: str, handler: EventHandler):
        """Subscribe to an event type. Use '*' for all events."""
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(handler)
            logger.debug(f"Subscribed to '{event_type}': {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: EventHandler):
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def publish(self, event: Event):
        """Publish an event to all subscribers."""
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            # Notify type-specific subscribers
            handlers = list(self._subscribers.get(event.type, []))
            # Notify wildcard subscribers
            handlers.extend(self._subscribers.get("*", []))

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler {handler.__name__} failed: {e}")

    def publish_simple(self, event_type: str, data: Dict = None,
                       source: str = "system"):
        """Convenience method to publish a simple event."""
        self.publish(Event(
            type=event_type, data=data or {},
            source=source,
        ))

    def history(self, event_type: Optional[str] = None,
                limit: int = 50) -> List[Event]:
        """Get recent event history."""
        with self._lock:
            if event_type:
                filtered = [e for e in self._history if e.type == event_type]
                return filtered[-limit:]
            return self._history[-limit:]

    def clear_history(self):
        with self._lock:
            self._history.clear()

    @property
    def status(self) -> dict:
        with self._lock:
            type_counts = defaultdict(int)
            for e in self._history:
                type_counts[e.type] += 1
            return {
                "subscribers": len(self._subscribers),
                "total_events": len(self._history),
                "by_type": dict(type_counts),
            }


# Global event bus
bus = EventBus()
