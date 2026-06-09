"""
LAAP — 变异策略
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import numpy as np, copy


@dataclass
class MutationSpec:
    name: str; description: str
    mutation_fn: Callable[[Dict[str, Any]], Dict[str, Any]]
    probability: float = 0.5; severity: float = 0.3


class MutationStrategy:
    def __init__(self):
        self.strategies: Dict[str, MutationSpec] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(MutationSpec("param_drift", "参数随机漂移", self._param_drift, 0.4, 0.2))
        self.register(MutationSpec("need_reweight", "需求权重重分配", self._need_reweight, 0.3, 0.3))
        self.register(MutationSpec("exploration_tune", "探索率调整", self._exploration_tune, 0.15, 0.25))
        self.register(MutationSpec("goal_reprioritize", "目标重排序", self._goal_reprioritize, 0.15, 0.3))

    def register(self, spec: MutationSpec):
        self.strategies[spec.name] = spec

    def select(self) -> MutationSpec:
        names = list(self.strategies.keys())
        probs = np.array([self.strategies[n].probability for n in names])
        probs /= probs.sum()
        return self.strategies[np.random.choice(names, p=probs)]

    def apply(self, state: Dict[str, Any], name: Optional[str] = None) -> Dict[str, Any]:
        spec = self.select() if name is None else self.strategies.get(name)
        if not spec:
            raise ValueError(f"Unknown strategy: {name}")
        return {
            "mutated": spec.mutation_fn(copy.deepcopy(state)),
            "strategy": spec.name, "severity": spec.severity,
        }

    @staticmethod
    def _param_drift(s):
        cfg = s.get("config", {})
        for k in ["exploration_rate", "learning_rate"]:
            if k in cfg:
                cfg[k] = np.clip(float(cfg[k]) + np.random.normal(0, 0.05), 0.01, 0.99)
        return s

    @staticmethod
    def _need_reweight(s):
        for n in s.get("needs", []):
            if "importance" in n:
                n["importance"] = max(0.2, min(3.0, float(n["importance"]) + np.random.normal(0, 0.15)))
        return s

    @staticmethod
    def _exploration_tune(s):
        cfg = s.get("config", {})
        if "exploration_rate" in cfg:
            delta = np.random.choice([-1, 1]) * np.random.uniform(0.05, 0.2)
            cfg["exploration_rate"] = np.clip(float(cfg["exploration_rate"]) + delta, 0.01, 0.99)
        return s

    @staticmethod
    def _goal_reprioritize(s):
        for g in s.get("goals", []):
            if "priority" in g:
                g["priority"] = np.clip(float(g["priority"]) + np.random.normal(0, 0.1), 0, 1)
        return s
