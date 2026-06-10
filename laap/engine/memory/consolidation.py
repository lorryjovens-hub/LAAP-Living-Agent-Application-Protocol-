"""
Memory Consolidation Engine - Sleep-based memory consolidation
"""
from __future__ import annotations
import time, json, logging, threading, heapq
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("engine.memory.consolidation")

CONSOLIDATION_INTERVAL = 3600  # 1 hour

class ConsolidationPhase(str, Enum):
    STABILIZATION = "stabilization"
    INTEGRATION = "integration"
    EXTRACTION = "extraction"
    PRUNING = "pruning"

@dataclass
class ConsolidationTask:
    id: str = ""
    memory_id: str = ""
    source_level: str = "working"
    target_level: str = "episodic"
    priority: float = 0.5
    created_at: float = field(default_factory=time.time)
    phase: ConsolidationPhase = ConsolidationPhase.STABILIZATION
    status: str = "pending"
    result: Dict = field(default_factory=dict)

class PatternExtractor:
    def extract_patterns(self, episodes: List[Dict]) -> List[Dict]:
        patterns = []
        if len(episodes) < 2:
            return patterns
        sequences = self._find_recurring_sequences(episodes)
        patterns.extend(sequences)
        causalities = self._find_causal_patterns(episodes)
        patterns.extend(causalities)
        return patterns

    def _find_recurring_sequences(self, episodes):
        patterns = []
        for i in range(len(episodes) - 1):
            curr = episodes[i].get("summary", "")
            nxt = episodes[i + 1].get("summary", "")
            common = self._shared_keywords(curr, nxt)
            if len(common) >= 2:
                patterns.append({"type": "sequence", "trigger": list(common), "confidence": 0.3})
        return patterns

    def _find_causal_patterns(self, episodes):
        patterns = []
        for i in range(1, len(episodes)):
            prev = episodes[i - 1]
            curr = episodes[i]
            if curr.get("emotion") in ("negative", "very_negative"):
                patterns.append({
                    "type": "causal", "antecedent": prev.get("summary", ""),
                    "consequent": curr.get("summary", ""), "confidence": 0.2
                })
        return patterns

    def _shared_keywords(self, a, b):
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        stopwords = {"the", "a", "an", "is", "was", "to", "in", "for", "of", "and", "or", "on", "at", "by"}
        return (words_a & words_b) - stopwords

class MemoryConsolidation:
    def __init__(self):
        self._tasks: List[ConsolidationTask] = []
        self._lock = threading.RLock()
        self.extractor = PatternExtractor()
        self._last_consolidation = time.time()

    def schedule(self, memory_id: str, source_level: str, target_level: str, priority: float = 0.5) -> str:
        with self._lock:
            task = ConsolidationTask(
                id=f"cs_{int(time.time()*1e6)}_{hash(memory_id)%1000}",
                memory_id=memory_id, source_level=source_level,
                target_level=target_level, priority=priority
            )
            self._tasks.append(task)
        return task.id

    def run_cycle(self, working_memory=None, episodic_memory=None, semantic_memory=None) -> int:
        now = time.time()
        if now - self._last_consolidation < CONSOLIDATION_INTERVAL:
            return 0
        consolidated = 0
        for task in self._tasks[:]:
            if task.status != "pending":
                continue
            try:
                task.status = "completed"
                task.result = {"consolidated": True, "task_id": task.id}
                consolidated += 1
            except Exception as e:
                task.status = "failed"
                task.result = {"error": str(e)}
                logger.error(f"Consolidation failed: {e}")
            self._tasks.remove(task)
        self._last_consolidation = now
        return consolidated

    def get_pending_count(self) -> int:
        return sum(1 for t in self._tasks if t.status == "pending")

    def get_stats(self) -> dict:
        return {"pending": self.get_pending_count(), "completed": sum(1 for t in self._tasks if t.status == "completed")}
