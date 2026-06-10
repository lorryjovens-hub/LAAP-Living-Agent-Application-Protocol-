"""
LAAP Memory Engine — Episodic Memory (情景记忆)
Autobiographical memory: stores past experiences with temporal and emotional context
"""

from __future__ import annotations
import time
import json
import uuid
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("engine.memory.episodic")


class EpisodeType(str, Enum):
    INTERACTION = "interaction"
    OBSERVATION = "observation"
    DECISION = "decision"
    ERROR = "error"
    LEARNING = "learning"
    EVOLUTION = "evolution"
    COMMUNICATION = "communication"
    GOAL_COMPLETION = "goal_completion"


class EmotionalValence(str, Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class Episode:
    id: str = field(default_factory=lambda: f"ep_{uuid.uuid4().hex[:12]}")
    type: EpisodeType = EpisodeType.OBSERVATION
    summary: str = ""
    content: Any = None
    context: Dict = field(default_factory=dict)
    emotion: EmotionalValence = EmotionalValence.NEUTRAL
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0
    tags: List[str] = field(default_factory=list)
    related_episodes: List[str] = field(default_factory=list)
    consolidated: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type.value,
            "summary": self.summary[:200],
            "emotion": self.emotion.value, "importance": self.importance,
            "timestamp": self.timestamp, "duration": self.duration,
            "tags": self.tags, "related": self.related_episodes,
            "consolidated": self.consolidated,
        }


class EpisodicMemory:
    """情景记忆 - 存储过去经验的时间序列"""
    
    def __init__(self, max_episodes: int = 10000):
        self._episodes: Dict[str, Episode] = {}
        self._timeline: List[str] = []
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._type_index: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        self.max_episodes = max_episodes
    
    def store(self, episode: Episode) -> str:
        with self._lock:
            self._episodes[episode.id] = episode
            self._timeline.append(episode.id)
            for tag in episode.tags:
                self._tag_index[tag].add(episode.id)
            self._type_index[episode.type.value].add(episode.id)
            if len(self._episodes) > self.max_episodes:
                self._trim_oldest()
        return episode.id
    
    def create_episode(self, ep_type: EpisodeType, summary: str, content: Any = None,
                       context: Dict = None, emotion: EmotionalValence = EmotionalValence.NEUTRAL,
                       importance: float = 0.5, tags: List[str] = None) -> str:
        ep = Episode(type=ep_type, summary=summary, content=content,
                     context=context or {}, emotion=emotion,
                     importance=importance, tags=tags or [])
        return self.store(ep)
    
    def recall(self, episode_id: str) -> Optional[Episode]:
        return self._episodes.get(episode_id)
    
    def recall_recent(self, n: int = 10) -> List[Episode]:
        recent_ids = self._timeline[-n:]
        return [self._episodes[eid] for eid in recent_ids if eid in self._episodes]
    
    def recall_by_type(self, ep_type: EpisodeType, limit: int = 20) -> List[Episode]:
        ids = list(self._type_index.get(ep_type.value, set()))[-limit:]
        return [self._episodes[eid] for eid in ids if eid in self._episodes]
    
    def recall_by_tag(self, tag: str, limit: int = 20) -> List[Episode]:
        ids = list(self._tag_index.get(tag, set()))[-limit:]
        return [self._episodes[eid] for eid in ids if eid in self._episodes]
    
    def recall_by_time_range(self, start: float, end: float) -> List[Episode]:
        return [ep for ep in self._episodes.values() if start <= ep.timestamp <= end]
    
    def recall_important(self, threshold: float = 0.7, limit: int = 20) -> List[Episode]:
        sorted_eps = sorted(self._episodes.values(), key=lambda e: e.importance, reverse=True)
        return [ep for ep in sorted_eps if ep.importance >= threshold][:limit]
    
    def recall_by_emotion(self, emotion: EmotionalValence, limit: int = 20) -> List[Episode]:
        ids = [eid for eid, ep in self._episodes.items() if ep.emotion == emotion]
        return [self._episodes[eid] for eid in ids[-limit:]]
    
    def find_similar(self, query: str, n: int = 5) -> List[Episode]:
        query_lower = query.lower()
        scores = []
        for ep in self._episodes.values():
            score = 0
            if query_lower in ep.summary.lower():
                score += 10
            for tag in ep.tags:
                if query_lower in tag.lower():
                    score += 5
            if ep.content and query_lower in str(ep.content).lower():
                score += 3
            if score > 0:
                scores.append((ep, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [ep for ep, _ in scores[:n]]
    
    def link_episodes(self, ep1_id: str, ep2_id: str):
        ep1 = self._episodes.get(ep1_id)
        ep2 = self._episodes.get(ep2_id)
        if ep1 and ep2:
            if ep2_id not in ep1.related_episodes:
                ep1.related_episodes.append(ep2_id)
            if ep1_id not in ep2.related_episodes:
                ep2.related_episodes.append(ep1_id)
    
    def build_timeline(self, start_time: float = 0) -> List[Episode]:
        sorted_eps = sorted(self._episodes.values(), key=lambda e: e.timestamp)
        return [ep for ep in sorted_eps if ep.timestamp >= start_time]
    
    def get_statistics(self) -> dict:
        type_counts = defaultdict(int)
        for ep in self._episodes.values():
            type_counts[ep.type.value] += 1
        return {
            "total_episodes": len(self._episodes),
            "timeline_span_days": (max(e.timestamp for e in self._episodes.values()) - min(e.timestamp for e in self._episodes.values())) / 86400 if self._episodes else 0,
            "by_type": dict(type_counts),
            "avg_importance": sum(e.importance for e in self._episodes.values()) / max(len(self._episodes), 1),
            "consolidated": sum(1 for e in self._episodes.values() if e.consolidated),
        }
    
    def search(self, query: str) -> List[Episode]:
        return self.find_similar(query, n=10)
    
    def _trim_oldest(self):
        while len(self._episodes) > self.max_episodes * 0.9:
            oldest = self._timeline.pop(0)
            ep = self._episodes.pop(oldest, None)
            if ep:
                for tag in ep.tags:
                    if tag in self._tag_index:
                        self._tag_index[tag].discard(oldest)
                self._type_index[ep.type.value].discard(oldest)


class TimelineIndex:
    """时间线索引 - 按时间维度快速检索"""
    
    def __init__(self):
        self._by_hour: Dict[int, List[str]] = defaultdict(list)
        self._by_day: Dict[str, List[str]] = defaultdict(list)
        self._by_week: Dict[str, List[str]] = defaultdict(list)
    
    def index(self, episode_id: str, timestamp: float):
        hour_key = int(timestamp // 3600)
        day_key = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
        week_key = time.strftime("%Y-W%W", time.gmtime(timestamp))
        self._by_hour[hour_key].append(episode_id)
        self._by_day[day_key].append(episode_id)
        self._by_week[week_key].append(episode_id)
    
    def get_by_hour(self, hour: int) -> List[str]:
        return self._by_hour.get(hour, [])
    
    def get_by_day(self, day: str) -> List[str]:
        return self._by_day.get(day, [])
    
    def get_by_week(self, week: str) -> List[str]:
        return self._by_week.get(week, [])
    
    def get_range(self, start_hour: int, end_hour: int) -> List[str]:
        result = []
        for h in range(start_hour, end_hour + 1):
            result.extend(self._by_hour.get(h, []))
        return result
