"""Tests for forgetting curve"""
from laap.engine.memory.forgetting import *

def test_ebbinghaus():
    curve = EbbinghausForgettingCurve()
    prob = curve.recall_probability(t_hours=1, importance=0.9)
    assert 0 < prob <= 1.0

def test_composite_curve():
    curve = CompositeForgettingCurve()
    prob = curve.compute(importance=0.8, age_hours=24, access_count=5)
    assert 0 <= prob <= 1.0

def test_sm2_review():
    item = SM2ReviewItem("test_item")
    item.review(4)
    assert item.ease_factor >= 1.3
