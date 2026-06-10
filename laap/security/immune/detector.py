"""Threat Detector — 威胁检测引擎"""
from __future__ import annotations
import time, json, logging, threading, hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("security.immune.detector")

class ThreatLevel(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ThreatEvent:
    id: str = ""
    type: str = ""
    source: str = ""
    level: ThreatLevel = ThreatLevel.INFO
    description: str = ""
    details: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class ThreatDetector:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._events: List[ThreatEvent] = []
        self._lock = threading.RLock()
    def register_handler(self, threat_type: str, handler: Callable):
        self._handlers[threat_type].append(handler)
    def detect(self, threat_type: str, source: str, description: str, details: Dict = None) -> ThreatEvent:
        event = ThreatEvent(
            id=f"thr_{int(time.time()*1e6)}_{hashlib.md5(source.encode()).hexdigest()[:8]}",
            type=threat_type, source=source, description=description, details=details or {}
        )
        for handler in self._handlers.get(threat_type, []):
            try:
                level = handler(event)
                if level:
                    event.level = ThreatLevel(level)
            except Exception as e:
                logger.error(f"Handler error: {e}")
        with self._lock:
            self._events.append(event)
            if len(self._events) > 1000:
                self._events = self._events[-1000:]
        return event
    def get_recent(self, n: int = 50) -> List[ThreatEvent]:
        with self._lock:
            return self._events[-n:]
    def get_by_level(self, level: ThreatLevel) -> List[ThreatEvent]:
        with self._lock:
            return [e for e in self._events if e.level == level]

class AnomalyDetector:
    def __init__(self, window_size: int = 100):
        self._baselines: Dict[str, List[float]] = defaultdict(lambda: [])
        self.window_size = window_size
        self._lock = threading.RLock()
    def learn_baseline(self, metric: str, value: float):
        with self._lock:
            self._baselines[metric].append(value)
            if len(self._baselines[metric]) > self.window_size:
                self._baselines[metric] = self._baselines[metric][-self.window_size:]
    def is_anomalous(self, metric: str, value: float, sigma: float = 2.0) -> Tuple[bool, float]:
        with self._lock:
            values = self._baselines.get(metric, [])
            if len(values) < 5:
                return False, 0.0
            mean = sum(values) / len(values)
            variance = sum((v - mean)**2 for v in values) / len(values)
            std = variance ** 0.5
            if std == 0:
                return False, 0.0
            z_score = abs(value - mean) / std
            return z_score > sigma, z_score

class SignatureMatcher:
    def __init__(self):
        self._signatures: Dict[str, Dict] = {}
    def add_signature(self, name: str, pattern: str, level: str = "medium"):
        self._signatures[name] = {"pattern": pattern, "level": level}
    def match(self, data: str) -> List[Tuple[str, str]]:
        matches = []
        for name, sig in self._signatures.items():
            if sig["pattern"] in data:
                matches.append((name, sig["level"]))
        return matches
