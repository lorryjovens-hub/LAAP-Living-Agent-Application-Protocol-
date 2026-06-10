"""Tests for working memory"""
from laap.engine.memory.working import *

def test_store_and_recall():
    wm = WorkingMemory()
    chunk = wm.store("test content")
    recalled = wm.recall(chunk.id)
    assert recalled == "test content"

def test_capacity():
    wm = WorkingMemory(capacity=3)
    for i in range(5):
        wm.store(f"item_{i}")
    assert wm.store.size() <= 3

def test_context_manager():
    cm = ContextManager()
    cm.push({"user": "alice"})
    context = cm.get_context_snapshot()
    assert context["history_depth"] == 1
