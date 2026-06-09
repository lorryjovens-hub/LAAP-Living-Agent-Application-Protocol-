"""
LAAP — Telemetry & Metrics

Collect, aggregate, and report system metrics.
"""

from __future__ import annotations
import json, logging, time, threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("laap.telemetry")


@dataclass
class MetricPoint:
    """A single data point in a metric series"""
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


class Metric:
    """A named metric with time series data"""
    def __init__(self, name: str, description: str = "", unit: str = ""):
        self.name = name
        self.description = description
        self.unit = unit
        self._points: List[MetricPoint] = []

    def record(self, value: float, labels: Optional[Dict[str, str]] = None):
        self._points.append(MetricPoint(value=value, labels=labels or {}))

    def average(self, window: int = 0) -> float:
        pts = self._points[-window:] if window > 0 else self._points
        if not pts:
            return 0.0
        return sum(p.value for p in pts) / len(pts)

    def last(self) -> Optional[float]:
        if not self._points:
            return None
        return self._points[-1].value

    def count(self) -> int:
        return len(self._points)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "unit": self.unit,
            "count": self.count(),
            "last": self.last(),
            "average": self.average(100),
        }


class MetricsCollector:
    """Central metrics collection and reporting"""

    def __init__(self):
        self._lock = threading.Lock()
        self._metrics: Dict[str, Metric] = {}
        self._auto_init()

    def _auto_init(self):
        defaults = [
            ("llm.calls", "Total LLM API calls", "count"),
            ("llm.tokens", "Total tokens used", "tokens"),
            ("llm.latency_ms", "LLM response latency", "ms"),
            ("tools.calls", "Total tool calls", "count"),
            ("tools.errors", "Total tool errors", "count"),
            ("tools.latency_ms", "Tool execution latency", "ms"),
            ("agent.steps", "Agent steps taken", "count"),
            ("agent.reward", "Agent intrinsic reward", "score"),
            ("memory.items", "Memory items stored", "count"),
            ("memory.forgotten", "Memory items forgotten", "count"),
            ("session.turns", "Session turns", "count"),
            ("session.tokens", "Session tokens", "tokens"),
        ]
        for name, desc, unit in defaults:
            self._metrics[name] = Metric(name=name, description=desc, unit=unit)

    def get(self, name: str) -> Metric:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Metric(name=name)
            return self._metrics[name]

    def record(self, name: str, value: float,
               labels: Optional[Dict[str, str]] = None):
        self.get(name).record(value, labels=labels)

    def increment(self, name: str, delta: float = 1.0,
                  labels: Optional[Dict[str, str]] = None):
        metric = self.get(name)
        last = metric.last() or 0.0
        metric.record(last + delta, labels=labels)

    def report(self) -> Dict[str, Any]:
        with self._lock:
            return {
                name: metric.to_dict()
                for name, metric in self._metrics.items()
            }

    def to_dict(self) -> dict:
        return self.report()


metrics = MetricsCollector()
