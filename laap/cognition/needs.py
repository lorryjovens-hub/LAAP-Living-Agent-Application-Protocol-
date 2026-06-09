"""
LAAP — 需求驱动系统

基于 Dörner PSI 理论的五大核心需求驱动引擎。
每个智能体都有内在需求，驱动其自主行动。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger("laap.cognition.needs")


class NeedType(Enum):
    CERTAINTY = "certainty"     # 确定性 — 对环境预测能力的需求
    COMPETENCE = "competence"   # 胜任感 — 能力成长与 mastery
    AUTONOMY = "autonomy"       # 自主性 — 自我决定的需求
    RELATEDNESS = "relatedness" # 归属感 — 社交连接的需求
    ENERGY = "energy"           # 能量 — 资源获取的需求


@dataclass
class Need:
    type: NeedType
    current_level: float = 0.5
    target_level: float = 0.8
    decay_rate: float = 0.01
    importance: float = 1.0
    volatility: float = 0.05

    def compute_drive(self) -> float:
        deficit = max(0.0, self.target_level - self.current_level)
        return deficit * self.importance

    def tick(self, dt: float = 1.0) -> float:
        decay = self.decay_rate * dt
        noise = np.random.normal(0, self.volatility * dt)
        self.current_level = np.clip(self.current_level - decay + noise, 0.0, 1.0)
        return self.current_level

    def satisfy(self, amount: float):
        self.current_level = min(1.0, self.current_level + amount)

    @property
    def deficit(self) -> float:
        return max(0.0, self.target_level - self.current_level)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "current": round(self.current_level, 3),
            "target": self.target_level,
            "drive": round(self.compute_drive(), 3),
            "deficit": round(self.deficit, 3),
        }


class NeedDriveSystem:
    """PSI 需求驱动系统"""

    def __init__(self, config: Optional[Dict[str, dict]] = None):
        self.needs: Dict[NeedType, Need] = {}
        self.tick_count = 0
        self._init_defaults()
        if config:
            self._apply_config(config)

    def _init_defaults(self):
        defaults = {
            NeedType.CERTAINTY:   Need(NeedType.CERTAINTY,   0.6, 0.8, 0.008, 1.2, 0.04),
            NeedType.COMPETENCE:  Need(NeedType.COMPETENCE,  0.4, 0.9, 0.012, 1.5, 0.06),
            NeedType.AUTONOMY:    Need(NeedType.AUTONOMY,    0.5, 0.7, 0.005, 1.0, 0.03),
            NeedType.RELATEDNESS: Need(NeedType.RELATEDNESS, 0.5, 0.7, 0.010, 0.8, 0.05),
            NeedType.ENERGY:      Need(NeedType.ENERGY,      0.7, 0.8, 0.015, 1.3, 0.04),
        }
        for nt, need in defaults.items():
            self.needs[nt] = need

    def _apply_config(self, config: Dict[str, dict]):
        for need_str, params in config.items():
            try:
                nt = NeedType(need_str)
            except ValueError:
                continue
            if nt in self.needs:
                for k, v in params.items():
                    if hasattr(self.needs[nt], k):
                        setattr(self.needs[nt], k, v)

    def tick(self, dt: float = 1.0) -> Dict[NeedType, float]:
        self.tick_count += 1
        return {nt: self.needs[nt].tick(dt) for nt in self.needs}

    def satisfy(self, need_type: NeedType, amount: float):
        if need_type in self.needs:
            self.needs[need_type].satisfy(amount)

    def get_dominant_need(self) -> Tuple[Optional[NeedType], float]:
        best_type, best_drive = None, -1.0
        for need in self.needs.values():
            d = need.compute_drive()
            if d > best_drive:
                best_drive, best_type = d, need.type
        return best_type, best_drive

    def get_drive_vector(self) -> Dict[str, float]:
        return {nt.value: self.needs[nt].compute_drive() for nt in self.needs}

    @property
    def emotional_valence(self) -> float:
        avg = np.mean([self.needs[nt].current_level for nt in self.needs])
        return 2.0 * avg - 1.0

    def get_profile(self) -> dict:
        return {nt.value: self.needs[nt].to_dict() for nt in self.needs}
