"""Zone 4: Production Deployment & Monitoring"""
from __future__ import annotations
import time, json, logging, threading, math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from laap.engine.evolution.proposal import EvolutionProposal, ProposalStatus

logger = logging.getLogger("engine.evolution.zone4")

class ContinuousMonitor:
    def __init__(self, window_size: int = 60):
        self._metrics_window: List[Dict] = []
        self.window_size = window_size
        self._baseline: Dict = {}
        self._lock = threading.RLock()
    def set_baseline(self, metrics: Dict):
        self._baseline = metrics.copy()
    def record(self, metrics: Dict):
        with self._lock:
            self._metrics_window.append(metrics)
            if len(self._metrics_window) > self.window_size:
                self._metrics_window = self._metrics_window[-self.window_size:]
    def get_current(self) -> Dict:
        with self._lock:
            if not self._metrics_window:
                return {}
            latest = self._metrics_window[-1]
            return latest
    def check_degradation(self, threshold: float = 0.1) -> List[str]:
        degraded = []
        if not self._baseline:
            return degraded
        current = self.get_current()
        for key, base_val in self._baseline.items():
            curr_val = current.get(key, base_val)
            if base_val > 0:
                ratio = (curr_val - base_val) / base_val
                if abs(ratio) > threshold:
                    degraded.append(f"{key}: {ratio:.1%}")
        return degraded

class Deployer:
    def deploy(self, proposal: EvolutionProposal) -> bool:
        logger.info(f"Production deploy: {proposal.id}")
        proposal.status = ProposalStatus.DEPLOYED
        return True
    def rollback(self, proposal: EvolutionProposal):
        logger.warning(f"Production rollback: {proposal.id}")
        proposal.status = ProposalStatus.ROLLED_BACK

class AutoRollbackTrigger:
    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold
    def should_rollback(self, baseline: Dict, current: Dict) -> bool:
        for key, base_val in baseline.items():
            curr_val = current.get(key, base_val)
            if base_val > 0:
                degradation = (base_val - curr_val) / base_val
                if degradation > self.threshold:
                    logger.warning(f"Auto-rollback triggered: {key} degraded {degradation:.1%}")
                    return True
        return False
