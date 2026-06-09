"""AEvo — 受保护评估器 (Protected Evaluator)"""
from __future__ import annotations
from typing import Any, Optional, Tuple
import logging
import numpy as np

logger = logging.getLogger("laap.evolution.aevo.eval")

_FORBIDDEN = {"__builtins__", "__import__", "eval", "exec", "os.system",
              "subprocess", "shutil.rmtree"}


class ProtectedEvaluator:
    """受保护评估器 — 防 Reward Hacking"""

    def __init__(self, base_evaluator, validation_enabled: bool = True):
        self._eval = base_evaluator
        self.validation_enabled = validation_enabled
        self.evaluation_count = 0
        self.rejection_count = 0
        self.last_score = 0.5

    def evaluate(self, agent, candidate_params: Any = None) -> Tuple[float, bool]:
        if self.validation_enabled and candidate_params is not None:
            if not self._validate(candidate_params):
                self.rejection_count += 1
                return 0.0, False
        saved = self._snapshot(agent)
        try:
            score = self._eval.composite_fitness(agent)
        finally:
            self._restore(agent, saved)
        score = float(np.clip(score, 0.0, 1.0))
        if self.evaluation_count > 0 and abs(score - self.last_score) > 0.8:
            self.rejection_count += 1
            return 0.0, False
        self.last_score = score
        self.evaluation_count += 1
        return score, True

    def _validate(self, candidate: Any) -> bool:
        if candidate is None:
            return False
        if isinstance(candidate, dict):
            s = str(candidate).lower()
            if any(k in s for k in _FORBIDDEN):
                return False
        return True

    def _snapshot(self, agent) -> dict:
        return {"exploration_rate": getattr(agent.config, 'exploration_rate', None),
                "learning_rate": getattr(agent.config, 'learning_rate', None)}

    def _restore(self, agent, state: dict) -> None:
        for k, v in state.items():
            if v is not None and hasattr(agent.config, k):
                setattr(agent.config, k, v)

    def status(self) -> dict:
        return {"evaluations": self.evaluation_count, "rejections": self.rejection_count,
                "validation": self.validation_enabled, "last_score": round(self.last_score, 4)}
