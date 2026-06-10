"""Four-Zone Evolution Orchestrator"""
from __future__ import annotations
import time, json, logging, threading, uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from laap.engine.evolution.proposal import EvolutionProposal, ProposalStatus, ProposalFactory
from laap.engine.evolution.zone1_monitor import PerformanceMonitor, OpportunityDetector, SafetyChecker, ConstraintEnforcer
from laap.engine.evolution.zone2_testing import TestRunner, SandboxExecutor, BenchmarkComparator, SecurityScanner, TestResult
from laap.engine.evolution.zone3_rollout import ABTestFramework, TrafficRouter, PromotionDecider, CanaryDeployer, ABMetrics
from laap.engine.evolution.zone4_production import ContinuousMonitor, Deployer, AutoRollbackTrigger
from laap.engine.evolution.metrics_collector import MetricsCollector, AnomalyDetector
from laap.engine.evolution.rollback_manager import RollbackManager

logger = logging.getLogger("engine.evolution.orchestrator")

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_time: float = 300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.last_failure = 0.0
        self.state = "closed"
    def record_failure(self):
        self.failure_count += 1
        self.last_failure = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning("Circuit breaker OPENED")
    def record_success(self):
        self.failure_count = max(0, self.failure_count - 1)
        if self.state == "open" and time.time() - self.last_failure > self.recovery_time:
            self.state = "half-open"
    def is_open(self) -> bool:
        return self.state == "open"
    def reset(self):
        self.failure_count = 0
        self.state = "closed"


class EvolutionPipeline:
    """进化管道 - 串联四区流程"""
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.detector = OpportunityDetector(self.monitor)
        self.safety = SafetyChecker()
        self.test_runner = TestRunner()
        self.benchmark = BenchmarkComparator()
        self.ab_framework = ABTestFramework()
        self.promotion_decider = PromotionDecider()
        self.circuit_breaker = CircuitBreaker()
        self.pending: List[EvolutionProposal] = []
    
    def process_proposal(self, proposal: EvolutionProposal) -> str:
        if self.circuit_breaker.is_open():
            return "rejected"
        try:
            # Zone 2: test
            result = self.test_runner.run_tests(proposal)
            # Zone 3: ab test
            metrics = self.ab_framework.analyze()
            if not self.promotion_decider.should_promote(metrics):
                return "failed_ab"
            # Zone 4: deploy
            self.circuit_breaker.record_success()
            return "deployed"
        except Exception as e:
            self.circuit_breaker.record_failure()
            return f"error: {e}"


class FourZoneOrchestrator:
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.detector = OpportunityDetector(self.monitor)
        self.safety = SafetyChecker()
        self.pipeline = EvolutionPipeline()
        self.factory = ProposalFactory()
        self.collector = MetricsCollector()
        self.rollback_mgr = RollbackManager()
        self._history: List[Dict] = []
        self._lock = threading.RLock()
    def run_cycle(self) -> List[str]:
        events = []
        if self.pipeline.circuit_breaker.is_open():
            events.append("Circuit breaker open, skipping cycle")
            return events
        # Zone 1: generate proposals
        proposals = self.detector.detect()
        for p in proposals:
            if self.safety.check(p):
                p.constraints = {"min": 0.0, "max": 1.0, "type": "float"}
                self.pipeline.pending.append(p)
                events.append(f"Proposed: {p.target}")
        # Process pending
        for proposal in self.pipeline.pending[:]:
            result = self.pipeline.process_proposal(proposal)
            events.append(f"{proposal.id}: {result}")
            self._history.append({"time": time.time(), "id": proposal.id, "result": result})
            self.pipeline.pending.remove(proposal)
        self.collector.record("evolution_cycle", len(events))
        return events
    def get_stats(self) -> dict:
        return {"pending": len(self.pipeline.pending), "history": len(self._history),
                "circuit": self.pipeline.circuit_breaker.state,
                "success_rate": sum(1 for h in self._history if h["result"]=="deployed")/max(len(self._history),1)}
