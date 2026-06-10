"""Memory engine tests — 20+ test functions covering all memory types."""

import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List


class TestWorkingMemory:
    """Working memory tests."""

    def test_working_memory_create(self):
        from laap.engine.memory.working import WorkingMemory
        wm = WorkingMemory(capacity=5)
        assert wm.capacity == 5
        assert len(wm.items) == 0

    def test_working_memory_add(self):
        from laap.engine.memory.working import WorkingMemory
        wm = WorkingMemory(capacity=5)
        wm.add("item1")
        assert len(wm.items) == 1

    def test_working_memory_capacity_limit(self):
        from laap.engine.memory.working import WorkingMemory
        wm = WorkingMemory(capacity=3)
        for i in range(5):
            wm.add(f"item{i}")
        assert len(wm.items) == 3

    def test_working_memory_get(self):
        from laap.engine.memory.working import WorkingMemory
        wm = WorkingMemory(capacity=5)
        wm.add("test_item")
        item = wm.get("test_item")
        assert item is not None

    def test_working_memory_clear(self):
        from laap.engine.memory.working import WorkingMemory
        wm = WorkingMemory(capacity=5)
        wm.add("item1")
        wm.add("item2")
        wm.clear()
        assert len(wm.items) == 0

    def test_working_memory_lru_eviction(self):
        from laap.engine.memory.working import WorkingMemory
        wm = WorkingMemory(capacity=2)
        wm.add("a")
        wm.add("b")
        wm.get("a")  # a is now most recently used
        wm.add("c")  # should evict b (least recently used)
        assert wm.get("b") is None
        assert wm.get("a") is not None


class TestEpisodicMemory:
    """Episodic memory tests."""

    def test_episodic_memory_create(self):
        from laap.engine.memory.episodic import EpisodicMemory
        em = EpisodicMemory()
        assert em.episodes == []

    def test_episodic_memory_store(self):
        from laap.engine.memory.episodic import EpisodicMemory
        em = EpisodicMemory()
        em.store("user said hello", {"emotion": "neutral"})
        assert len(em.episodes) == 1

    def test_episodic_memory_recall(self):
        from laap.engine.memory.episodic import EpisodicMemory
        em = EpisodicMemory()
        em.store("meeting about project")
        results = em.recall("project")
        assert len(results) > 0

    def test_episodic_memory_with_timestamp(self):
        from laap.engine.memory.episodic import EpisodicMemory
        em = EpisodicMemory()
        now = datetime.now()
        em.store("event", timestamp=now)
        assert em.episodes[0]["timestamp"] == now

    def test_episodic_memory_empty_recall(self):
        from laap.engine.memory.episodic import EpisodicMemory
        em = EpisodicMemory()
        results = em.recall("nonexistent")
        assert results == []


class TestSemanticMemory:
    """Semantic memory tests."""

    def test_semantic_memory_create(self):
        from laap.engine.memory.semantic import SemanticMemory
        sm = SemanticMemory()
        assert sm.facts == {}

    def test_semantic_memory_learn(self):
        from laap.engine.memory.semantic import SemanticMemory
        sm = SemanticMemory()
        sm.learn("LAAP", "is an agent framework")
        assert "LAAP" in sm.facts

    def test_semantic_memory_query(self):
        from laap.engine.memory.semantic import SemanticMemory
        sm = SemanticMemory()
        sm.learn("Python", "is a programming language")
        result = sm.query("Python")
        assert result == "is a programming language"

    def test_semantic_memory_unknown_query(self):
        from laap.engine.memory.semantic import SemanticMemory
        sm = SemanticMemory()
        result = sm.query("UnknownConcept")
        assert result is None

    def test_semantic_memory_update_fact(self):
        from laap.engine.memory.semantic import SemanticMemory
        sm = SemanticMemory()
        sm.learn("LAAP", "is a framework")
        sm.learn("LAAP", "is an agent framework")
        assert sm.facts["LAAP"] == "is an agent framework"


class TestMuscleMemory:
    """Muscle/procedural memory tests."""

    def test_muscle_memory_create(self):
        from laap.engine.memory.muscle import MuscleMemory
        mm = MuscleMemory()
        assert mm.procedures == {}

    def test_muscle_memory_learn_procedure(self):
        from laap.engine.memory.muscle import MuscleMemory
        mm = MuscleMemory()
        mm.learn("greet", [{"say": "hello"}, {"wait": "response"}])
        assert "greet" in mm.procedures

    def test_muscle_memory_execute(self):
        from laap.engine.memory.muscle import MuscleMemory
        mm = MuscleMemory()
        steps = [{"say": "hello"}, {"say": "world"}]
        mm.learn("greet", steps)
        result = mm.execute("greet")
        assert result is True

    def test_muscle_memory_unknown_procedure(self):
        from laap.engine.memory.muscle import MuscleMemory
        mm = MuscleMemory()
        with pytest.raises(KeyError):
            mm.execute("unknown")


class TestForgettingCurve:
    """Forgetting curve engine tests."""

    def test_forgetting_curve_create(self):
        from laap.engine.memory.forgetting import ForgettingCurveEngine
        fce = ForgettingCurveEngine()
        assert fce is not None

    def test_forgetting_curve_calculate(self):
        from laap.engine.memory.forgetting import ForgettingCurveEngine
        fce = ForgettingCurveEngine()
        score = fce.calculate(strength=1.0, hours_elapsed=1)
        assert 0 <= score <= 1

    def test_forgetting_curve_review_update(self):
        from laap.engine.memory.forgetting import ForgettingCurveEngine
        fce = ForgettingCurveEngine()
        new_strength = fce.review(strength=0.5, performance=1.0)
        assert new_strength > 0.5

    def test_forgetting_curve_needs_review(self):
        from laap.engine.memory.forgetting import ForgettingCurveEngine
        fce = ForgettingCurveEngine()
        result = fce.needs_review(strength=0.1, threshold=0.3)
        assert result is True


class TestVectorStore:
    """Vector store tests."""

    def test_vector_store_create(self):
        from laap.engine.memory.vector_store import VectorStore
        vs = VectorStore(dimension=128)
        assert vs.dimension == 128

    def test_vector_store_add(self):
        from laap.engine.memory.vector_store import VectorStore
        vs = VectorStore(dimension=4)
        vs.add("id1", [0.1, 0.2, 0.3, 0.4], {"text": "hello"})
        assert vs.count == 1

    def test_vector_store_search(self):
        from laap.engine.memory.vector_store import VectorStore
        vs = VectorStore(dimension=4)
        vs.add("id1", [1.0, 0.0, 0.0, 0.0], {"text": "a"})
        vs.add("id2", [0.0, 1.0, 0.0, 0.0], {"text": "b"})
        results = vs.search([1.0, 0.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0]["id"] == "id1"

    def test_vector_store_delete(self):
        from laap.engine.memory.vector_store import VectorStore
        vs = VectorStore(dimension=4)
        vs.add("id1", [0.1, 0.2, 0.3, 0.4])
        vs.delete("id1")
        assert vs.count == 0

    def test_vector_store_empty_search(self):
        from laap.engine.memory.vector_store import VectorStore
        vs = VectorStore(dimension=4)
        results = vs.search([0.1, 0.2, 0.3, 0.4])
        assert results == []
