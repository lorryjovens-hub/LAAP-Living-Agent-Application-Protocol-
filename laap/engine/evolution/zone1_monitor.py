"""Zone 1: Constraint Generation & Monitoring"""
from __future__ import annotations
import time, json, logging, threading, math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from laap.engine.evolution.proposal import EvolutionProposal, ProposalStatus, RiskLevel, ProposalFactory

logger = logging.getLogger("engine.evolution.zone1")

@dataclass
class ThresholdConfig:
    response_time: float = 0.100
    error_rate: float = 0.01
    memory_hit_rate: float = 0.80
    throughput_min: float = 100.0

class MetricWindow:
    def __init__(self, window_size: int = 100):
        self.values: List[float] = []
        self.window_size = window_size
        self._lock = threading.RLock()
    def add(self, value: float):
        with self._lock:
            self.values.append(value)
            if len(self.values) > self.window_size:
                self.values = self.values[-self.window_size:]
    def avg(self) -> float:
        with self._lock:
            return sum(self.values) / max(len(self.values), 1)
    def p95(self) -> float:
        with self._lock:
            if not self.values:
                return 0.0
            sorted_vals = sorted(self.values)
            idx = int(len(sorted_vals) * 0.95)
            return sorted_vals[min(idx, len(sorted_vals)-1)]
    def latest(self) -> float:
        with self._lock:
            return self.values[-1] if self.values else 0.0

class PerformanceMonitor:
    def __init__(self):
        self._metrics: Dict[str, MetricWindow] = defaultdict(lambda: MetricWindow())
        self.thresholds = ThresholdConfig()
    def record(self, metric_name: str, value: float):
        self._metrics[metric_name].add(value)
    def get_metric(self, name: str) -> MetricWindow:
        return self._metrics[name]
    def check_degradation(self) -> List[Tuple[str, float, float]]:
        issues = []
        checks = [("response_time", self.thresholds.response_time),
                  ("error_rate", self.thresholds.error_rate)]
        for name, threshold in checks:
            m = self._metrics.get(name)
            if m and m.avg() > threshold * 1.2:
                issues.append((name, m.avg(), threshold))
        return issues

class OpportunityDetector:
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
    def detect(self) -> List[EvolutionProposal]:
        proposals = []
        for metric_name, avg, threshold in self.monitor.check_degradation():
            proposal = EvolutionProposal(
                target=f"system.{metric_name}",
                current_value=avg,
                proposed_value=avg * 0.8,
                rationale=f"{metric_name} degraded to {avg:.4f}, exceeding {threshold}",
                expected_gain=(avg - threshold) / max(threshold, 0.001),
                risk_level="medium" if (avg - threshold) / max(threshold, 0.001) < 0.5 else "high"
            )
            proposals.append(proposal)
        return proposals

class SafetyChecker:
    def check(self, proposal: EvolutionProposal) -> bool:
        checks = [
            proposal.constraints["min"] <= proposal.proposed_value <= proposal.constraints["max"],
            proposal.proposed_value != proposal.current_value,
            bool(proposal.rationale),
            proposal.expected_gain > 0,
        ]
        return all(checks)

class ConstraintEnforcer:
    def __init__(self):
        self._constraints: Dict[str, Dict] = {
            "temperature": {"min": 0.0, "max": 2.0, "type": "float"},
            "memory_threshold": {"min": 0.1, "max": 0.9, "type": "float"},
            "retry_count": {"min": 1, "max": 10, "type": "int"},
        }
    def get_constraints(self, target: str) -> Dict:
        return self._constraints.get(target, {"min": 0.0, "max": 1.0, "type": "float"})
