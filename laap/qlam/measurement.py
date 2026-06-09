"""
LAAP ⟷ QLAM — Query-Dependent Measurement
Retrieves task-relevant information from quantum states.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple


class QueryDependentMeasurement:
    def __init__(self, num_qubits: int = 6, num_measurements: int = 10):
        self.num_qubits = num_qubits
        self.num_measurements = num_measurements
        self.dim = 1 << num_qubits

    def measure(self, state: List[float], query: Optional[Any] = None) -> List[Tuple[int, float]]:
        probabilities = [abs(x) ** 2 for x in state[:self.dim]]
        total = sum(probabilities) or 1.0
        probs = [p / total for p in probabilities]
        indexed = list(enumerate(probs))[:self.num_measurements]
        indexed.sort(key=lambda x: x[1], reverse=True)
        return indexed

    def sample(self, state: List[float], num_samples: int = 1) -> List[int]:
        flat = state[:self.dim]
        probs = [abs(x) ** 2 for x in flat]
        total = sum(probs) or 1.0
        probs = [p / total for p in probs]
        import random
        return random.choices(range(len(probs)), weights=probs, k=num_samples)

    def overlap(self, state_a: List[float], state_b: List[float]) -> float:
        n = min(len(state_a), len(state_b), self.dim)
        dot = sum(state_a[i] * state_b[i] for i in range(n))
        return abs(dot) ** 2
