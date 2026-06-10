"""Health Check System"""
from __future__ import annotations
import time, json, logging, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("infrastructure.monitoring.health")

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"

@dataclass
class HealthReport:
    status: HealthStatus = HealthStatus.HEALTHY
    component: str = ""
    message: str = ""
    latency_ms: float = 0.0
    checked_at: float = field(default_factory=time.time)

class HealthChecker:
    def __init__(self):
        self._checks: Dict[str, Callable] = {}
        self._results: Dict[str, HealthReport] = {}
        self._lock = threading.RLock()
    def register(self, name: str, check_fn: Callable):
        self._checks[name] = check_fn
    def run_all(self) -> Dict[str, HealthReport]:
        results = {}
        for name, fn in self._checks.items():
            try:
                start = time.time()
                status = fn()
                latency = (time.time() - start) * 1000
                report = HealthReport(status=HealthStatus(status) if isinstance(status, str) else HealthStatus.HEALTHY,
                                     component=name, latency_ms=round(latency, 2))
            except Exception as e:
                report = HealthReport(status=HealthStatus.DOWN, component=name, message=str(e))
            results[name] = report
            with self._lock:
                self._results[name] = report
        return results
    def get_status(self) -> HealthStatus:
        results = self.run_all()
        if any(r.status == HealthStatus.DOWN for r in results.values()):
            return HealthStatus.DOWN
        if any(r.status == HealthStatus.DEGRADED for r in results.values()):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY
