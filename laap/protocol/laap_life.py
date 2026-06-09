"""
LAAP-LIFE v1.0 — 数字生命体生命周期协议

确定性状态机 + 守卫条件 + 副作用:
- 状态: BORN → GROWING → MATURE → AGING → DYING → REBORN
- 事件: INIT/INTERACTION/TIMEOUT/ERROR/RECOVER
- 守卫: 每个变迁需要满足的条件
"""
from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("laap.protocol.life")


class LifeStage(str, Enum):
    UNBORN = "unborn"       # 模板
    BORN = "born"           # 刚出生
    GROWING = "growing"     # 成长
    MATURE = "mature"       # 成熟
    AGING = "aging"         # 衰老
    DYING = "dying"         # 死亡
    REBORN = "reborn"       # 重生

class LifeEventType(str, Enum):
    INIT_COMPLETE = "init_complete"
    INTERACTION = "interaction"
    SKILL_ACQUIRED = "skill_acquired"
    LEVEL_UP = "level_up"
    IDLE_TIMEOUT = "idle_timeout"
    RECOVER = "recover"
    ERROR = "error"
    CRITICAL = "critical"
    RESTORE = "restore"
    AGE_MILESTONE = "age_milestone"


@dataclass
class LifeEvent:
    type: LifeEventType
    data: Any = None
    timestamp: float = field(default_factory=time.time)


class LifecycleStateMachine:
    """
    确定性状态机——数字生命体的"心脏"
    所有状态变迁可追踪、可验证、可回放
    """

    # 状态变迁表: (当前状态, 事件) → 目标状态
    TRANSITIONS: Dict[Tuple[LifeStage, LifeEventType], LifeStage] = {
        (LifeStage.UNBORN, LifeEventType.INIT_COMPLETE): LifeStage.BORN,
        (LifeStage.BORN, LifeEventType.INIT_COMPLETE): LifeStage.GROWING,
        (LifeStage.GROWING, LifeEventType.INTERACTION): LifeStage.GROWING,
        (LifeStage.GROWING, LifeEventType.LEVEL_UP): LifeStage.MATURE,
        (LifeStage.GROWING, LifeEventType.IDLE_TIMEOUT): LifeStage.AGING,
        (LifeStage.GROWING, LifeEventType.ERROR): LifeStage.GROWING,
        (LifeStage.MATURE, LifeEventType.INTERACTION): LifeStage.MATURE,
        (LifeStage.MATURE, LifeEventType.IDLE_TIMEOUT): LifeStage.AGING,
        (LifeStage.MATURE, LifeEventType.ERROR): LifeStage.DYING,
        (LifeStage.AGING, LifeEventType.INTERACTION): LifeStage.GROWING,
        (LifeStage.AGING, LifeEventType.IDLE_TIMEOUT): LifeStage.DYING,
        (LifeStage.AGING, LifeEventType.RECOVER): LifeStage.MATURE,
        (LifeStage.DYING, LifeEventType.RESTORE): LifeStage.REBORN,
        (LifeStage.REBORN, LifeEventType.INIT_COMPLETE): LifeStage.GROWING,
    }

    def __init__(self, initial: LifeStage = LifeStage.UNBORN):
        self._current = initial
        self._history: List[Dict] = []
        self._guards: Dict[Tuple[LifeStage, LifeEventType], Callable] = {}
        self._effects: Dict[Tuple[LifeStage, LifeEventType], Callable] = {}
        self._last_active_time = time.time()

    def add_guard(self, stage: LifeStage, event: LifeEventType,
                  guard_fn: Callable[[], bool]):
        """添加守卫条件"""
        self._guards[(stage, event)] = guard_fn

    def add_effect(self, stage: LifeStage, event: LifeEventType,
                   effect_fn: Callable):
        """添加副作用"""
        self._effects[(stage, event)] = effect_fn

    def trigger(self, event: LifeEvent) -> bool:
        """触发事件，尝试状态变迁"""
        key = (self._current, event.type)
        target = self.TRANSITIONS.get(key)

        if target is None:
            logger.debug(f"No transition for {self._current} + {event.type}")
            return False

        # 检查守卫
        guard = self._guards.get(key)
        if guard and not guard():
            logger.info(f"Guard blocked: {self._current} → {target} ({event.type})")
            return False

        # 执行变迁
        old = self._current
        self._current = target
        self._last_active_time = time.time()

        # 执行副作用
        effect = self._effects.get(key)
        if effect:
            try:
                effect()
            except Exception as e:
                logger.warning(f"Effect failed: {e}")

        # 记录历史
        self._history.append({
            "time": event.timestamp,
            "from": old.value,
            "to": target.value,
            "event": event.type.value,
        })
        logger.info(f"Lifecycle: {old.value} → {target.value}")
        return True

    @property
    def stage(self) -> LifeStage:
        return self._current

    @property
    def idle_hours(self) -> float:
        return (time.time() - self._last_active_time) / 3600

    def get_history(self, limit: int = 10) -> List[Dict]:
        return self._history[-limit:]

    def to_dict(self) -> dict:
        return {
            "stage": self._current.value,
            "idle_hours": round(self.idle_hours, 1),
            "history_count": len(self._history),
        }
