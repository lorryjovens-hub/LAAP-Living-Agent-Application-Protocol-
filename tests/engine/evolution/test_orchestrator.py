"""Tests for evolution orchestrator"""
from laap.engine.evolution.orchestrator import *

def test_circuit_breaker():
    cb = CircuitBreaker(failure_threshold=3)
    assert cb.is_open() == False
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open() == True
    cb.reset()
    assert cb.is_open() == False

def test_orchestrator_creation():
    orch = FourZoneOrchestrator()
    assert orch is not None
    assert orch.monitor is not None
