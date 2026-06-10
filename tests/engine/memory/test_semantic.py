"""Tests for semantic memory"""
from laap.engine.memory.semantic import *

def test_store_concept():
    sm = SemanticMemory()
    cid = sm.store_concept("Python", "Programming language")
    concept = sm.query("Python")
    assert concept is not None
    assert concept.name == "Python"

def test_relation():
    sm = SemanticMemory()
    sm.store_concept("Python")
    sm.store_concept("Programming")
    sm.relate("Python", "Programming", RelationType.IS_A)
    context = sm.get_context("Python", depth=1)
    assert context["found"] is True
