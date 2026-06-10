"""Metrics Collection — Counter, Gauge, Histogram"""
from __future__ import annotations
import time, json, threading, logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("infrastructure.monitoring.metrics")

class Metric:
    def __init__(self, name: str, help_text: str = "", labels: Dict = None):
        self.name = name
        self.help_text = help_text
        self.labels = labels or {}

class Counter(Metric):
    def __init__(self, name: str, help_text: str = ""):
        super().__init__(name, help_text)
        self._value = 0.0
        self._lock = threading.RLock()
    def inc(self, amount: float = 1.0):
        with self._lock:
            self._value += amount
    def get(self) -> float:
        with self._lock:
            return self._value
    def reset(self):
        with self._lock:
            self._value = 0.0

class Gauge(Metric):
    def __init__(self, name: str, help_text: str = ""):
        super().__init__(name, help_text)
        self._value = 0.0
        self._lock = threading.RLock()
    def set(self, value: float):
        with self._lock:
            self._value = value
    def inc(self, amount: float = 1.0):
        with self._lock:
            self._value += amount
    def dec(self, amount: float = 1.0):
        with self._lock:
            self._value -= amount
    def get(self) -> float:
        with self._lock:
            return self._value

class Histogram(Metric):
    def __init__(self, name: str, help_text: str = "", buckets: List[float] = None):
        super().__init__(name, help_text)
        self.buckets = sorted(buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
        self._counts = [0] * len(self.buckets)
        self._sum = 0.0
        self._count = 0
        self._lock = threading.RLock()
    def observe(self, value: float):
        with self._lock:
            self._sum += value
            self._count += 1
            for i, b in enumerate(self.buckets):
                if value <= b:
                    self._counts[i] += 1
                    break
    def get_stats(self) -> Dict:
        with self._lock:
            return {"count": self._count, "sum": self._sum, "avg": self._sum/max(self._count,1)}

class MetricRegistry:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._metrics = {}
            cls._instance._lock = threading.RLock()
        return cls._instance
    def counter(self, name: str, help_text: str = "") -> Counter:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Counter(name, help_text)
            return self._metrics[name]
    def gauge(self, name: str, help_text: str = "") -> Gauge:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Gauge(name, help_text)
            return self._metrics[name]
    def histogram(self, name: str, help_text: str = "") -> Histogram:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Histogram(name, help_text)
            return self._metrics[name]
    def prometheus_export(self) -> str:
        lines = []
        for name, metric in self._metrics.items():
            lines.append(f"# HELP {name} {metric.help_text}")
            lines.append(f"# TYPE {name} {type(metric).__name__.lower()}")
            if isinstance(metric, Counter):
                lines.append(f"{name} {metric.get()}")
            elif isinstance(metric, Gauge):
                lines.append(f"{name} {metric.get()}")
            elif isinstance(metric, Histogram):
                stats = metric.get_stats()
                lines.append(f'{name}_count {stats["count"]}')
                lines.append(f'{name}_sum {stats["sum"]}')
        return "\n".join(lines)
