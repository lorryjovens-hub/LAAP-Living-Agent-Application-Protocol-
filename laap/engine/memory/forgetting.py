"""LAAP Memory Engine — Forgetting Curve (遗忘曲线)
Ebbinghaus exponential decay model with SM-2 spaced repetition
"""
from __future__ import annotations
import math, time, logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("engine.memory.forgetting")

class EbbinghausForgettingCurve:
    @staticmethod
    def recall_probability(t_hours: float, importance: float = 0.5,
                           half_life_hours: float = 168, recall_count: int = 0) -> float:
        """P(recall) = importance * 2^(-t / half_life) where half_life grows with recalls"""
        adjusted_hl = half_life_hours * (1 + 0.3 * math.log(1 + recall_count))
        adjusted_hl *= (1 + 2 * importance)
        return importance * (2 ** (-t_hours / max(adjusted_hl, 1)))
    
    @staticmethod
    def strength_decay(initial_strength: float, t_hours: float, decay_rate: float = 0.1) -> float:
        return initial_strength * math.exp(-decay_rate * t_hours)
    
    @staticmethod
    def retrieval_strength(study_count: int, t_hours_since_last: float, decay: float = 0.1) -> float:
        return 1 - math.exp(-study_count / (1 + decay * t_hours_since_last))
    
    @staticmethod
    def storage_strength(study_count: int, avg_interval: float) -> float:
        return 1 - 2 ** (-study_count / (1 + avg_interval / 24))

class CompositeForgettingCurve:
    def __init__(self):
        self.ebbinghaus = EbbinghausForgettingCurve()
    
    def compute(self, importance: float, age_hours: float, access_count: int,
                half_life_hours: float = 168, frequency: float = 0.0) -> float:
        base = self.ebbinghaus.recall_probability(age_hours, importance, half_life_hours, access_count)
        freq_boost = frequency * (1 - 2 ** (-age_hours / max(half_life_hours * 0.5, 1)))
        return min(1.0, base + freq_boost * 0.3)
    
    def needs_review(self, importance: float, age_hours: float, access_count: int,
                     threshold: float = 0.3) -> Tuple[bool, float]:
        prob = self.compute(importance, age_hours, access_count)
        return prob < threshold, prob

class SM2ReviewItem:
    def __init__(self, item_id: str, ease_factor: float = 2.5, interval: int = 1, repetitions: int = 0):
        self.item_id = item_id
        self.ease_factor = ease_factor
        self.interval = interval
        self.repetitions = repetitions
        self.next_review = time.time() + interval * 3600
        self.last_quality: int = 0
    
    def review(self, quality: int):
        """SM-2 algorithm: quality 0-5"""
        self.last_quality = quality
        if quality < 3:
            self.repetitions = 0
            self.interval = 1
        else:
            self.repetitions += 1
            if self.repetitions == 1:
                self.interval = 1
            elif self.repetitions == 2:
                self.interval = 6
            else:
                self.interval = int(self.interval * self.ease_factor)
            self.ease_factor = max(1.3, self.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        self.next_review = time.time() + self.interval * 3600

class ReviewScheduler:
    def __init__(self):
        self._items: Dict[str, SM2ReviewItem] = {}
    
    def add_item(self, item_id: str):
        self._items[item_id] = SM2ReviewItem(item_id)
    
    def record_review(self, item_id: str, quality: int):
        if item_id in self._items:
            self._items[item_id].review(quality)
    
    def get_due_items(self) -> List[str]:
        now = time.time()
        return [iid for iid, item in self._items.items() if item.next_review <= now]
    
    def get_stats(self) -> dict:
        return {"total": len(self._items), "due": len(self.get_due_items())}
