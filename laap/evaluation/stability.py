# -*- coding: utf-8 -*-
"""LAAP - Stability Monitor"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time, numpy as np


@dataclass
class StabilityAlert:
    level: str; component: str; message: str
    value: float; threshold: float
    timestamp: float = field(default_factory=time.time)


class StabilityMonitor:
    def __init__(self):
        self.alerts: List[StabilityAlert] = []
        self._valence_buffer = []

    def check(self, agent) -> List[StabilityAlert]:
        new = []
        v = agent.emotion_gradient.state.valence
        if v < -0.7:
            new.append(StabilityAlert("critical", "emotion", f"情绪效价严重偏负 ({v:.2f})", v, -0.7))
        elif v < -0.4:
            new.append(StabilityAlert("warning", "emotion", f"情绪效价偏负 ({v:.2f})", v, -0.4))
        levels = [agent.needs.needs[nt].current_level for nt in agent.needs.needs]
        std_need = float(np.std(levels))
        if std_need > 0.35:
            new.append(StabilityAlert("warning", "needs", f"需求不均衡 (std={std_need:.2f})", std_need, 0.35))
        self.alerts.extend(new)
        return new
