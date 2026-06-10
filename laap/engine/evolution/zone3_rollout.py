"""Zone 3: Staged Rollout & A/B Testing"""
from __future__ import annotations
import time, json, logging, threading, random, math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from laap.engine.evolution.proposal import EvolutionProposal, ProposalStatus

logger = logging.getLogger("engine.evolution.zone3")

@dataclass
class ABMetrics:
    control_mean: float = 0.0
    experiment_mean: float = 0.0
    improvement: float = 0.0
    confidence: float = 0.0
    duration_minutes: int = 0
    sample_size: int = 0

class TrafficRouter:
    def __init__(self):
        self._weights: Dict[str, float] = {"control": 0.99, "experiment": 0.01}
    def route(self, request_id: str) -> str:
        h = hash(request_id) % 10000
        threshold = int(self._weights["experiment"] * 10000)
        return "experiment" if h < threshold else "control"
    def set_experiment_weight(self, weight: float):
        self._weights["experiment"] = min(0.5, max(0.001, weight))
        self._weights["control"] = 1.0 - self._weights["experiment"]

class ABTestFramework:
    def __init__(self):
        self.router = TrafficRouter()
        self._control_metrics: List[float] = []
        self._experiment_metrics: List[float] = []
        self._lock = threading.RLock()
    def record_control(self, value: float):
        with self._lock:
            self._control_metrics.append(value)
    def record_experiment(self, value: float):
        with self._lock:
            self._experiment_metrics.append(value)
    def analyze(self) -> ABMetrics:
        with self._lock:
            c = self._control_metrics
            e = self._experiment_metrics
            if not c or not e:
                return ABMetrics()
            c_mean = sum(c) / len(c)
            e_mean = sum(e) / len(e)
            improvement = (c_mean - e_mean) / max(c_mean, 0.001) * 100 if c_mean > 0 else 0
            n1, n2 = len(c), len(e)
            var1 = sum((x - c_mean)**2 for x in c) / max(n1-1, 1)
            var2 = sum((x - e_mean)**2 for x in e) / max(n2-1, 1)
            se = math.sqrt(var1/n1 + var2/n2) if (n1 > 0 and n2 > 0) else 0
            t_stat = (c_mean - e_mean) / max(se, 0.001) if se > 0 else 0
            df = min(n1, n2) - 1
            confidence = min(0.99, abs(t_stat) / (df + 1)) if df > 0 else 0.5
            return ABMetrics(control_mean=c_mean, experiment_mean=e_mean,
                           improvement=improvement, confidence=confidence,
                           sample_size=n1 + n2)

class PromotionDecider:
    def should_promote(self, metrics: ABMetrics, threshold: float = 0.05) -> bool:
        return metrics.improvement > threshold * 100 and metrics.confidence > 0.95

class CanaryDeployer:
    def deploy(self, proposal: EvolutionProposal, weight: float = 0.01) -> bool:
        logger.info(f"Canary deploying {proposal.id} at {weight:.1%}")
        proposal.status = ProposalStatus.STAGING
        return True
    def rollback(self, proposal: EvolutionProposal):
        logger.warning(f"Canary rollback: {proposal.id}")
        proposal.status = ProposalStatus.ROLLED_BACK
