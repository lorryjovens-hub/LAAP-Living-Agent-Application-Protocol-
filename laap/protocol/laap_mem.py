"""
LAAP-MEM v1.0 — 记忆协议

分层记忆架构 (参考 Atkinson-Shiffrin 人类记忆模型):
- 工作记忆: 当前上下文 (Redis/内存)
- 情景记忆: 过去经历 (SQLite)
- 语义记忆: 知识概念 (向量数据库)
- 肌肉记忆: 熟练技能 (缓存/编译)
"""
from __future__ import annotations
import json
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("laap.protocol.mem")


class MemoryLevel(str, Enum):
    WORKING = "working"       # 工作记忆 (秒级)
    EPISODIC = "episodic"     # 情景记忆 (天级)
    SEMANTIC = "semantic"     # 语义记忆 (持久)
    MUSCLE = "muscle"         # 肌肉记忆 (固化)


class MemoryType(str, Enum):
    FACT = "fact"             # 事实
    EVENT = "event"           # 事件
    SKILL = "skill"           # 技能
    CONCEPT = "concept"       # 概念
    PREFERENCE = "preference" # 偏好
    RELATION = "relation"     # 关系


@dataclass
class MemoryRecord:
    """标准记忆记录格式"""
    id: str = ""
    level: MemoryLevel = MemoryLevel.WORKING
    type: MemoryType = MemoryType.FACT
    content: str = ""
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5        # 0-1
    timestamp: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    access_count: int = 0
    source: str = ""               # 来源 LAAP-ID 或 user
    embedding: List[float] = field(default_factory=list)


class ForgettingCurve:
    """
    艾宾浩斯遗忘曲线
    recall(t) = importance * 2^(-t / half_life)
    """

    @staticmethod
    def recall_probability(importance: float, age_hours: float,
                           half_life_hours: float = 168) -> float:
        """计算在 t 时刻的回忆概率"""
        hl = half_life_hours * (1 + 2 * importance)  # 重要记忆半衰期更长
        return importance * (2 ** (-age_hours / hl))

    @staticmethod
    def needs_review(importance: float, age_hours: float,
                     threshold: float = 0.3) -> bool:
        """是否需要复习（回忆概率低于阈值）"""
        return ForgettingCurve.recall_probability(importance, age_hours) < threshold


class MemoryStore:
    """记忆存储——分层记忆的实现"""

    def __init__(self):
        self._working: List[MemoryRecord] = []      # 工作记忆 (内存)
        self._episodic: List[MemoryRecord] = []     # 情景记忆
        self._semantic: Dict[str, MemoryRecord] = {} # 语义记忆
        self._consolidation_threshold = 3           # 访问3次后巩固

    def store(self, record: MemoryRecord) -> str:
        """存储记忆（自动归入合适的分层）"""
        import uuid
        record.id = record.id or f"mem_{uuid.uuid4().hex[:12]}"
        record.last_access = time.time()

        # 自动分层
        if record.level == MemoryLevel.WORKING:
            self._working.append(record)
            # 如果工作记忆太长，触发巩固
            if len(self._working) > 20:
                self._consolidate()
        elif record.level == MemoryLevel.EPISODIC:
            self._episodic.append(record)
        else:
            self._semantic[record.id] = record

        logger.debug(f"Memory stored: {record.id[:12]} ({record.level.value})")
        return record.id

    def recall(self, query: str, limit: int = 10,
               min_importance: float = 0.0) -> List[MemoryRecord]:
        """召回记忆（所有分层联合搜索）"""
        results = []
        query_lower = query.lower()

        # 搜索所有分层
        for record in self._working + self._episodic + list(self._semantic.values()):
            relevance = 0.0
            # 关键词匹配
            if query_lower in record.content.lower():
                relevance += 0.5
            for tag in record.tags:
                if query_lower in tag.lower():
                    relevance += 0.3
            # 遗忘曲线
            age_hours = (time.time() - record.timestamp) / 3600
            recall_prob = ForgettingCurve.recall_probability(
                record.importance, age_hours
            )
            relevance += recall_prob * 0.2

            if relevance > 0 and record.importance >= min_importance:
                results.append((relevance, record))
                record.access_count += 1
                record.last_access = time.time()

        # 按相关性排序
        results.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in results[:limit]]

    def _consolidate(self):
        """记忆巩固：工作记忆 → 情景记忆（类似睡眠）"""
        for record in self._working:
            if record.access_count >= self._consolidation_threshold:
                record.level = MemoryLevel.EPISODIC
                self._episodic.append(record)
                logger.debug(f"Consolidated: {record.id[:12]} → episodic")
        self._working.clear()

    def get_stats(self) -> dict:
        return {
            "working": len(self._working),
            "episodic": len(self._episodic),
            "semantic": len(self._semantic),
        }
