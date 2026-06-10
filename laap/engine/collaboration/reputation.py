"""Reputation System — 信誉系统"""
from __future__ import annotations
import time, math, logging, threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("engine.collaboration.reputation")

@dataclass
class ReputationRecord:
    identity: str = ""
    score: float = 0.5
    total_interactions: int = 0
    successful: int = 0
    failed: int = 0
    last_updated: float = field(default_factory=time.time)
    history: List[Dict] = field(default_factory=list)

class ReputationSystem:
    def __init__(self, decay_rate: float = 0.95):
        self.decay_rate = decay_rate
        self._records: Dict[str, ReputationRecord] = {}
        self._lock = threading.RLock()
    def record_interaction(self, identity: str, success: bool, value: float = 0.1):
        with self._lock:
            if identity not in self._records:
                self._records[identity] = ReputationRecord(identity=identity)
            rec = self._records[identity]
            rec.total_interactions += 1
            if success:
                rec.successful += 1
                rec.score = min(1.0, rec.score + value)
            else:
                rec.failed += 1
                rec.score = max(0.0, rec.score - value * 2)
            rec.last_updated = time.time()
            rec.history.append({"time": time.time(), "success": success, "score": rec.score})
            if len(rec.history) > 100:
                rec.history = rec.history[-100:]
    def get_score(self, identity: str) -> float:
        with self._lock:
            rec = self._records.get(identity)
            if rec:
                age = time.time() - rec.last_updated
                decayed = rec.score * (self.decay_rate ** (age / 86400))
                return round(decayed, 4)
            return 0.5
    def get_trustworthy(self, threshold: float = 0.7) -> List[str]:
        return [i for i in self._records if self.get_score(i) >= threshold]
    def get_stats(self) -> dict:
        return {"records": len(self._records), "avg_score": sum(r.score for r in self._records.values())/max(len(self._records),1)}
