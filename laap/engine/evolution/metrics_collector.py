"""Metrics Collection & Anomaly Detection"""
from __future__ import annotations
import time, math, logging, threading, statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("engine.evolution.metrics")

@dataclass
class TimeSeriesPoint:
    timestamp: float = 0.0
    value: float = 0.0
    labels: Dict = field(default_factory=dict)

class MetricsCollector:
    def __init__(self, retention_hours: int = 24):
        self._series: Dict[str, List[TimeSeriesPoint]] = defaultdict(list)
        self.retention_seconds = retention_hours * 3600
        self._lock = threading.RLock()
    def record(self, name: str, value: float, labels: Dict = None):
        with self._lock:
            self._series[name].append(TimeSeriesPoint(time.time(), value, labels or {}))
            self._truncate(name)
    def _truncate(self, name: str):
        cutoff = time.time() - self.retention_seconds
        self._series[name] = [p for p in self._series[name] if p.timestamp >= cutoff]
    def get_series(self, name: str, minutes: int = 60) -> List[TimeSeriesPoint]:
        cutoff = time.time() - minutes * 60
        with self._lock:
            return [p for p in self._series.get(name, []) if p.timestamp >= cutoff]
    def get_latest(self, name: str) -> Optional[float]:
        series = self._series.get(name, [])
        return series[-1].value if series else None
    def avg(self, name: str, minutes: int = 60) -> float:
        points = self.get_series(name, minutes)
        return sum(p.value for p in points) / max(len(points), 1)

class AnomalyDetector:
    def __init__(self, sigma_threshold: float = 3.0):
        self.sigma_threshold = sigma_threshold
    def detect(self, values: List[float]) -> List[int]:
        if len(values) < 3:
            return []
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0
        if std == 0:
            return []
        anomalies = []
        for i, v in enumerate(values):
            z_score = abs(v - mean) / std
            if z_score > self.sigma_threshold:
                anomalies.append(i)
        return anomalies
    def is_anomalous(self, value: float, reference: List[float]) -> bool:
        if len(reference) < 3:
            return False
        mean = statistics.mean(reference)
        std = statistics.stdev(reference)
        return abs(value - mean) / max(std, 0.001) > self.sigma_threshold
