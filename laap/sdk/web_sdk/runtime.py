"""Web Runtime — 浏览器运行时"""
from __future__ import annotations
import time, json, logging, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("sdk.web.runtime")

class RuntimeState(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    TERMINATED = "terminated"

class WebRuntime:
    def __init__(self, app_id: str = ""):
        self.app_id = app_id
        self.state = RuntimeState.INITIALIZING
        self._handlers: Dict[str, Callable] = {}
        self._storage: Dict[str, Any] = {}
        self._lock = threading.RLock()
    def initialize(self, config: Dict = None) -> bool:
        try:
            self.state = RuntimeState.RUNNING
            logger.info(f"WebRuntime initialized: {self.app_id}")
            return True
        except Exception as e:
            self.state = RuntimeState.ERROR
            logger.error(f"Init failed: {e}")
            return False
    def handle_event(self, event_type: str, data: Any = None) -> Any:
        handler = self._handlers.get(event_type)
        if handler:
            return handler(data)
        return None
    def on(self, event_type: str, handler: Callable):
        self._handlers[event_type] = handler
    def store(self, key: str, value: Any):
        with self._lock:
            self._storage[key] = value
    def load(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._storage.get(key)
    def get_state(self) -> Dict:
        return {"app_id": self.app_id, "state": self.state.value, "handlers": len(self._handlers)}
    def shutdown(self):
        self.state = RuntimeState.TERMINATED
        logger.info("WebRuntime shutdown")
