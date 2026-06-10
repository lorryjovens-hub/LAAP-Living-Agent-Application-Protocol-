"""Evolution engine tests — 15+ test functions covering proposals, monitoring, breakers, orchestration, rollback."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta
from typing import Dict, Any, List


class TestProposalCreate:
    """Proposal creation and management."""

    def test_proposal_create(self):
        from laap.engine.evolution.proposal import Proposal
        p = Proposal(
            proposal_id="prop-1",
            title="Improve memory",
            description="Optimize vector store",
            author="agent-1",
        )
        assert p.proposal_id == "prop-1"

    def test_proposal_status_default(self):
        from laap.engine.evolution.proposal import Proposal
        p = Proposal(proposal_id="p1", title="t", description="d", author="a")
        assert p.status == "draft"

    def test_proposal_submit(self):
        from laap.engine.evolution.proposal import Proposal
        p = Proposal(proposal_id="p1", title="t", description="d", author="a")
        p.submit()
        assert p.status == "submitted"

    def test_proposal_approve(self):
        from laap.engine.evolution.proposal import Proposal
        p = Proposal(proposal_id="p1", title="t", description="d", author="a")
        p.submit()
        p.approve()
        assert p.status == "approved"

    def test_proposal_reject(self):
        from laap.engine.evolution.proposal import Proposal
        p = Proposal(proposal_id="p1", title="t", description="d", author="a")
        p.submit()
        p.reject(reason="Not needed")
        assert p.status == "rejected"

    def test_proposal_vote(self):
        from laap.engine.evolution.proposal import Proposal
        p = Proposal(proposal_id="p1", title="t", description="d", author="a")
        p.submit()
        p.vote("agent-2", approve=True)
        assert p.votes["agent-2"] is True


class TestPerformanceMonitor:
    """Performance monitoring tests."""

    def test_monitor_create(self):
        from laap.engine.evolution.metrics_collector import MetricsCollector
        mc = MetricsCollector()
        assert mc.metrics == {}

    def test_monitor_record(self):
        from laap.engine.evolution.metrics_collector import MetricsCollector
        mc = MetricsCollector()
        mc.record("response_time", 0.5)
        assert "response_time" in mc.metrics

    def test_monitor_average(self):
        from laap.engine.evolution.metrics_collector import MetricsCollector
        mc = MetricsCollector()
        mc.record("latency", 1.0)
        mc.record("latency", 2.0)
        mc.record("latency", 3.0)
        assert mc.average("latency") == 2.0

    def test_monitor_stats(self):
        from laap.engine.evolution.metrics_collector import MetricsCollector
        mc = MetricsCollector()
        mc.record("t", 10)
        mc.record("t", 20)
        mc.record("t", 30)
        s = mc.stats("t")
        assert s["min"] == 10
        assert s["max"] == 30


class TestCircuitBreaker:
    """Circuit breaker tests."""

    def test_breaker_create(self):
        from laap.engine.evolution.zone1_monitor import CircuitBreaker
        cb = CircuitBreaker(name="test", threshold=5)
        assert cb.name == "test"
        assert cb.state == "closed"

    def test_breaker_record_failure(self):
        from laap.engine.evolution.zone1_monitor import CircuitBreaker
        cb = CircuitBreaker(name="test", threshold=3)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == "open"

    def test_breaker_reset(self):
        from laap.engine.evolution.zone1_monitor import CircuitBreaker
        cb = CircuitBreaker(name="test", threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        cb.reset()
        assert cb.state == "closed"

    def test_breaker_half_open(self):
        from laap.engine.evolution.zone1_monitor import CircuitBreaker
        cb = CircuitBreaker(name="test", threshold=2, recovery_timeout=0)
        cb.record_failure()
        cb.record_failure()
        cb.try_half_open()
        assert cb.state == "half-open"


class TestOrchestrator:
    """Orchestrator tests."""

    def test_orchestrator_create(self):
        from laap.engine.evolution.orchestrator import EvolutionOrchestrator
        orch = EvolutionOrchestrator()
        assert orch is not None

    def test_orchestrator_start_cycle(self):
        from laap.engine.evolution.orchestrator import EvolutionOrchestrator
        orch = EvolutionOrchestrator()
        result = orch.start_cycle()
        assert result is True

    def test_orchestrator_get_status(self):
        from laap.engine.evolution.orchestrator import EvolutionOrchestrator
        orch = EvolutionOrchestrator()
        status = orch.get_status()
        assert "phase" in status

    def test_orchestrator_stop(self):
        from laap.engine.evolution.orchestrator import EvolutionOrchestrator
        orch = EvolutionOrchestrator()
        orch.start_cycle()
        result = orch.stop()
        assert result is True


class TestRollback:
    """Rollback manager tests."""

    def test_rollback_create(self):
        from laap.engine.evolution.rollback_manager import RollbackManager
        rm = RollbackManager()
        assert rm.snapshots == []

    def test_rollback_snapshot(self):
        from laap.engine.evolution.rollback_manager import RollbackManager
        rm = RollbackManager()
        snap_id = rm.create_snapshot({"config": "v1"})
        assert snap_id is not None
        assert len(rm.snapshots) == 1

    def test_rollback_restore(self):
        from laap.engine.evolution.rollback_manager import RollbackManager
        rm = RollbackManager()
        snap_id = rm.create_snapshot({"config": "v1"})
        rm.create_snapshot({"config": "v2"})
        result = rm.restore(snap_id)
        assert result["config"] == "v1"

    def test_rollback_latest(self):
        from laap.engine.evolution.rollback_manager import RollbackManager
        rm = RollbackManager()
        rm.create_snapshot({"config": "v1"})
        latest = rm.get_latest()
        assert latest is not None
