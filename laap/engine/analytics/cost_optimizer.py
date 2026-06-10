"""Cost Optimizer for Progressive Analytics"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class StrategyCost:
    name: str = ""
    compute_cost: float = 0.0
    storage_cost: float = 0.0
    latency_ms: float = 0.0
    accuracy: float = 1.0

class CostModel:
    COMPUTE_UNIT_COST = 0.00001
    STORAGE_UNIT_COST = 0.000001
    def estimate(self, strategy: str, data_size: float) -> StrategyCost:
        costs = {
            "streaming": StrategyCost("streaming", 0.1, 0.01, 1, 0.999),
            "hierarchical": StrategyCost("hierarchical", 1.0, 0.5, 100, 0.99),
            "sampling": StrategyCost("sampling", 0.5, 0.1, 1000, 0.95),
            "exact": StrategyCost("exact", 10.0, 5.0, 10000, 1.0),
        }
        base = costs.get(strategy, costs["exact"])
        return StrategyCost(
            name=base.name,
            compute_cost=base.compute_cost * data_size,
            storage_cost=base.storage_cost * data_size,
            latency_ms=base.latency_ms,
            accuracy=base.accuracy,
        )

class ValueEstimator:
    def estimate(self, task_importance: float, decision_sensitivity: float, accuracy: float) -> float:
        info_gain = accuracy * task_importance
        return info_gain * decision_sensitivity

class BudgetManager:
    def __init__(self, total_budget: float = 100000.0):
        self.total_budget = total_budget
        self.spent = 0.0
    def allocate(self, task_id: str, cost: float) -> bool:
        if self.spent + cost <= self.total_budget:
            self.spent += cost
            return True
        return False
    def remaining(self) -> float:
        return self.total_budget - self.spent
    def reset(self):
        self.spent = 0.0
