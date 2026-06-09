"""
LAAP — 目标层级系统 (GoalTree)

PSI 理论中需求驱动目标形成。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import uuid; import numpy as np


class GoalStatus(Enum):
    INACTIVE = "inactive"; ACTIVE = "active"
    IN_PROGRESS = "in_progress"; COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Goal:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""; description: str = ""
    priority: float = 0.5; progress: float = 0.0
    status: GoalStatus = GoalStatus.INACTIVE
    parent_id: Optional[str] = None
    subgoals: List[Goal] = field(default_factory=list)
    need_type: Optional[str] = None
    completion_count: int = 0; fail_count: int = 0

    def activate(self): self.status = GoalStatus.ACTIVE
    def advance(self, amount=0.1) -> float:
        self.progress = min(1.0, self.progress + amount)
        if self.progress >= 1.0:
            self.status = GoalStatus.COMPLETED; self.completion_count += 1
        else: self.status = GoalStatus.IN_PROGRESS
        return self.progress
    def fail(self): self.status = GoalStatus.FAILED; self.fail_count += 1
    @property
    def is_terminal(self) -> bool: return len(self.subgoals) == 0
    @property
    def success_rate(self) -> float:
        t = self.completion_count + self.fail_count
        return self.completion_count / t if t > 0 else 0.5
    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name,
                "status": self.status.value, "progress": round(self.progress, 2)}


class GoalTree:
    def __init__(self):
        self.root: Optional[Goal] = None
        self._goal_map: Dict[str, Goal] = {}
    def set_root(self, g: Goal):
        self.root = g; self._goal_map[g.id] = g
    def add_subgoal(self, pid: str, sub: Goal) -> bool:
        p = self._goal_map.get(pid)
        if not p: return False
        sub.parent_id = pid; p.subgoals.append(sub); self._goal_map[sub.id] = sub
        return True
    def select_next(self, dv: Dict[str, float]) -> Optional[Goal]:
        candidates = self._executable()
        if not candidates: return None
        best, bs = None, -float("inf")
        for g in candidates:
            nd = dv.get(g.need_type or "", 0.5)
            score = g.priority * nd * (1.0 - g.progress) * g.success_rate + np.random.normal(0, 0.1)
            if score > bs: bs, best = score, g
        return best
    def _executable(self) -> List[Goal]:
        r = []; self._collect(self.root, r); return r
    def _collect(self, g, r):
        if g is None: return
        if g.is_terminal and g.status in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS, GoalStatus.INACTIVE): r.append(g)
        for s in g.subgoals: self._collect(s, r)

    def get_active(self) -> List[Goal]:
        """获取所有活跃目标"""
        results = []
        self._collect_active(self.root, results)
        return results

    def _collect_active(self, g, results):
        if g is None: return
        if g.status in (GoalStatus.ACTIVE, GoalStatus.IN_PROGRESS):
            results.append(g)
        for s in g.subgoals: self._collect_active(s, results)

    def to_dict(self) -> dict:
        """序列化为字典"""
        active = self.get_active()
        return {
            "root": self.root.name if self.root else None,
            "active_count": len(active),
            "active": [g.to_dict() for g in active[:5]],
        }
