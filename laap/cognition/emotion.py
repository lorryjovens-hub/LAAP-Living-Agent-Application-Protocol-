"""
LAAP — 情绪梯度系统 (EG-MRSI)

情绪 = 需求满足率的微分信号，不是标签，而是指导 RSI 改进的方向。
基于 EG-MRSI (Ando 2025) 框架。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class EmotionalState:
    valence: float = 0.0
    arousal: float = 0.5
    dominance: float = 0.5
    confidence: float = 0.5

    def to_dict(self) -> dict:
        return {
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "dominance": round(self.dominance, 3),
            "confidence": round(self.confidence, 3),
        }


class EmotionGradient:
    def __init__(self, alpha=1.0, beta=0.5, gamma=0.8, smoothing=0.3):
        self.alpha = alpha; self.beta = beta; self.gamma = gamma
        self.smoothing = smoothing
        self.state = EmotionalState()
        self._need_history: List[Dict[str, float]] = []
        self._reward_history: List[float] = []

    def update(self, satisfactions: Dict[str, float],
               task_success: Optional[float] = None,
               novelty: Optional[float] = None) -> EmotionalState:
        self._need_history.append(satisfactions)
        avg = np.mean(list(satisfactions.values()))
        v_target = np.clip(2.0 * avg - 1.0, -1.0, 1.0)
        self.state.valence = self._smooth(self.state.valence, v_target)

        if len(self._need_history) >= 2:
            prev = self._need_history[-2]; curr = self._need_history[-1]
            deltas = [curr[k] - prev.get(k, 0.5) for k in curr]
            drive = min(1.0, abs(np.mean(deltas)) * 3)
        else:
            drive = 0.3
        self.state.arousal = self._smooth(self.state.arousal, 0.3 + 0.7 * drive)

        if task_success is not None:
            self.state.dominance = self._smooth(self.state.dominance, 0.2 + 0.8 * task_success)
        if novelty is not None:
            self.state.confidence = self._smooth(self.state.confidence, np.clip(1.0 - novelty, 0, 1))
        return self.state

    def compute_intrinsic_reward(self) -> float:
        vd = 0.0
        if len(self._need_history) >= 2:
            vd = np.mean(list(self._need_history[-1].values())) - np.mean(list(self._need_history[-2].values()))
        r = np.clip(self.alpha * vd + self.beta * (1.0 - self.state.confidence) + self.gamma * self.state.arousal, -1.0, 1.0)
        self._reward_history.append(float(r))
        return float(r)

    @property
    def mean_reward(self, window=20) -> float:
        r = self._reward_history[-window:] if self._reward_history else [0.0]
        return float(np.mean(r))

    @property
    def reward_volatility(self, window=20) -> float:
        if len(self._reward_history) < window:
            return 0.0
        return float(np.std(self._reward_history[-window:]))

    def _smooth(self, old, new):
        return old * self.smoothing + new * (1.0 - self.smoothing)

    def reset(self):
        self.state = EmotionalState()
        self._need_history.clear(); self._reward_history.clear()
