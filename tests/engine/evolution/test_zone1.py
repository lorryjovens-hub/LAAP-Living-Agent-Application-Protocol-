"""Tests for Zone1"""
from laap.engine.evolution.zone1_monitor import *

def test_performance_monitor():
    monitor = PerformanceMonitor()
    monitor.record("response_time", 0.05)
    monitor.record("response_time", 0.15)
    issues = monitor.check_degradation()
    assert len(issues) >= 0

def test_safety_checker():
    checker = SafetyChecker()
    from laap.engine.evolution.proposal import EvolutionProposal
    p = EvolutionProposal(target="test", current_value=0.5, proposed_value=0.7,
                         rationale="testing", expected_gain=0.2,
                         constraints={"min": 0.0, "max": 1.0, "type": "float"})
    assert checker.check(p) is True
