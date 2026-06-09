"""LAAP - Fitness Evaluator

Multi-dimensional agent fitness evaluation for RSI and population selection.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
import numpy as np


class FitnessEvaluator:
    """综合适应度评估"""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "need_satisfaction": 0.25,
            "emotional_health": 0.20,
            "performance": 0.25,
            "stability": 0.15,
            "growth_rate": 0.15,
        }

    def composite_fitness(self, agent) -> float:
        scores = self._compute(agent)
        fitness = sum(scores[k] * self.weights.get(k, 0.0) for k in scores)
        return float(np.clip(fitness, 0.0, 1.0))

    def _compute(self, agent) -> Dict[str, float]:
        return {
            "need_satisfaction": self._need_score(agent),
            "emotional_health": self._emotion_score(agent),
            "performance": self._performance_score(agent),
            "stability": self._stability_score(agent),
            "growth_rate": self._growth_score(agent),
        }

    def _need_score(self, agent) -> float:
        if not hasattr(agent, 'needs') or not agent.needs:
            return 0.5
        try:
            levels = [agent.needs.needs[nt].current_level for nt in agent.needs.needs]
            return float(np.clip(np.mean(levels) * 0.7 + (1.0 - np.std(levels)) * 0.3, 0, 1))
        except Exception:
            return 0.5

    def _emotion_score(self, agent) -> float:
        eg = getattr(agent, 'emotion_gradient', None)
        if not eg:
            return 0.5
        v = (eg.state.valence + 1.0) / 2.0
        c = eg.state.confidence
        d = eg.state.dominance
        return float(np.clip(0.4 * v + 0.4 * c + 0.2 * d, 0, 1))

    def _performance_score(self, agent) -> float:
        hist = getattr(agent, "_reward_history", None)
        if hist is None:
            eg = getattr(agent, 'emotion_gradient', None)
            hist = getattr(eg, '_reward_history', []) if eg else []
        if not hist:
            return 0.5
        recent = hist[-20:] if len(hist) >= 20 else hist
        return float(np.clip((np.mean(recent) + 1.0) / 2.0, 0, 1))

    def _stability_score(self, agent) -> float:
        eg = getattr(agent, 'emotion_gradient', None)
        vol = getattr(eg, 'reward_volatility', None) if eg else None
        if vol is None or vol == 0:
            return 0.5
        return float(np.clip(1.0 - vol, 0, 1))

    def _growth_score(self, agent) -> float:
        hist = getattr(agent, "_reward_history", None)
        if hist is None:
            eg = getattr(agent, 'emotion_gradient', None)
            hist = getattr(eg, '_reward_history', []) if eg else []
        if len(hist) < 10:
            return 0.5
        recent = np.array(hist[-10:])
        slope = recent[-1] - recent[0]
        return float(np.clip((slope + 1.0) / 2.0, 0, 1))

    def report(self, agent) -> Dict[str, Any]:
        scores = self._compute(agent)
        return {
            "fitness": round(self.composite_fitness(agent), 4),
            "scores": {k: round(v, 4) for k, v in scores.items()},
        }
