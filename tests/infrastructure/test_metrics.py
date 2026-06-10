"""Tests for metrics"""
from laap.infrastructure.monitoring.metrics import *

def test_counter():
    c = Counter("test_counter")
    c.inc()
    c.inc(5)
    assert c.get() == 6.0