"""AEvo — 进化候选历史 (Searchable Candidate History)"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import Counter
import time, uuid, logging
import numpy as np

logger = logging.getLogger("laap.evolution.aevo.history")


@dataclass
class CandidateRecord:
    """单个进化候选记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    step: int = 0
    description: str = ""
    fitness_before: float = 0.0
    fitness_after: float = 0.0
    success: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def score_delta(self) -> float:
        return self.fitness_after - self.fitness_before


class CandidateHistory:
    """进化候选历史 — 可搜索、可分析、可持久化"""

    def __init__(self, max_size: int = 1000):
        self.candidates: List[CandidateRecord] = []
        self.max_size = max_size

    def record(self, candidate: CandidateRecord) -> None:
        self.candidates.append(candidate)
        if len(self.candidates) > self.max_size:
            self.candidates = self.candidates[-self.max_size:]

    def record_result(self, *, step: int, description: str = "",
                      fitness_before: float, fitness_after: float,
                      success: bool, error: Optional[str] = None,
                      **metadata) -> CandidateRecord:
        record = CandidateRecord(
            step=step, description=description,
            fitness_before=fitness_before, fitness_after=fitness_after,
            success=success, error=error, metadata=metadata,
        )
        self.record(record)
        return record

    def search(self, success: Optional[bool] = None,
               min_delta: float = 0.0, max_results: int = 10) -> List[CandidateRecord]:
        results = [c for c in self.candidates
                   if (success is None or c.success == success)
                   and abs(c.score_delta) >= min_delta]
        return results[-max_results:]

    def best_k(self, k: int = 5) -> List[CandidateRecord]:
        scored = sorted(self.candidates, key=lambda c: c.score_delta, reverse=True)
        return [c for c in scored if c.success][:k]

    def fitness_trend(self, window: int = 20) -> List[float]:
        cands = self.candidates[-window:]
        return [c.fitness_after for c in cands]

    def failure_patterns(self) -> List[str]:
        failed = [c for c in self.candidates if not c.success and c.error]
        patterns = Counter(c.error for c in failed if c.error)
        return [f"{pattern} ({count}x)" for pattern, count in patterns.most_common(5)]

    def clear(self) -> None:
        self.candidates.clear()

    def summary(self) -> Dict[str, Any]:
        if not self.candidates:
            return {"total": 0}
        return {
            "total": len(self.candidates),
            "successful": sum(1 for c in self.candidates if c.success),
            "avg_delta": round(float(np.mean([c.score_delta for c in self.candidates])), 5),
            "best_delta": round(max((c.score_delta for c in self.candidates), default=0.0), 5),
            "failure_patterns": self.failure_patterns(),
        }
