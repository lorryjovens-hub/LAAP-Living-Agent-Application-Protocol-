"""Tests for streaming algorithms"""
from laap.engine.analytics.streaming import *

def test_count_min_sketch():
    cms = CountMinSketch(width=100, depth=5)
    for i in range(1000):
        cms.add("item_a")
    est = cms.estimate("item_a")
    assert est >= 950  # Should be close to 1000

def test_hyperloglog():
    hll = HyperLogLog(precision=10)
    for i in range(10000):
        hll.add(f"unique_item_{i}")
    est = hll.estimate()
    assert 8000 <= est <= 12000  # Should be close to 10000
