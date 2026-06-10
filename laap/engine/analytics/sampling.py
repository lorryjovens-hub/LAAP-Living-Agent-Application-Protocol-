"""Adaptive Sampling Engine"""
from __future__ import annotations
import math, time, random
from collections import defaultdict
from typing import Any, Dict, List, Optional

class AdaptiveSampler:
    def __init__(self, base_rate: float = 0.001, min_rate: float = 0.0001, max_rate: float = 1.0):
        self.base_rate = base_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self._uncertainty: Dict[str, float] = defaultdict(lambda: 1.0)
    def should_sample(self, segment: str, current_estimate: float = 0.0) -> bool:
        uncertainty = self._uncertainty[segment]
        prob = min(self.max_rate, self.base_rate * (1 + 10 * uncertainty))
        return random.random() < prob
    def update_uncertainty(self, segment: str, estimate: float, actual: float):
        error = abs(estimate - actual) / max(abs(actual), 0.001)
        old = self._uncertainty[segment]
        self._uncertainty[segment] = 0.7 * old + 0.3 * min(error, 1.0)
    def get_sampling_rate(self, segment: str) -> float:
        return self.base_rate * (1 + 10 * self._uncertainty[segment])

class StratifiedSampler:
    def __init__(self):
        self._strata: Dict[str, Dict] = {}
    def add_stratum(self, name: str, proportion: float):
        self._strata[name] = {"proportion": proportion, "sampled": 0, "total": 0}
    def record(self, stratum: str):
        if stratum in self._strata:
            self._strata[stratum]["total"] += 1
    def sample(self, stratum: str) -> bool:
        if stratum not in self._strata:
            return False
        s = self._strata[stratum]
        target = int(s["proportion"] * max(s["total"], 1))
        if s["sampled"] < target:
            s["sampled"] += 1
            return True
        return False
    def get_stats(self) -> Dict:
        return {k: {"proportion": v["proportion"], "rate": v["sampled"]/max(v["total"],1)} for k,v in self._strata.items()}

class ReservoirSampler:
    def __init__(self, k: int = 1000):
        self.k = k
        self._samples: List[Any] = []
        self._count = 0
    def add(self, item: Any):
        self._count += 1
        if len(self._samples) < self.k:
            self._samples.append(item)
        else:
            r = random.randint(0, self._count - 1)
            if r < self.k:
                self._samples[r] = item
    def get_samples(self) -> List[Any]:
        return list(self._samples)
    def get_count(self) -> int:
        return self._count
