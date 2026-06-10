"""Hierarchical Aggregation Engine"""
from __future__ import annotations
import time, math, threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class TimeBucket:
    level: str = "minute"
    key: str = ""
    count: int = 0
    sum_value: float = 0.0
    min_value: float = float("inf")
    max_value: float = float("-inf")
    def update(self, value: float):
        self.count += 1
        self.sum_value += value
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)
    def avg(self) -> float:
        return self.sum_value / self.count if self.count else 0.0

class TimeHierarchy:
    LEVELS = ["second", "minute", "hour", "day", "week", "month"]
    def __init__(self):
        self._buckets: Dict[str, Dict[str, TimeBucket]] = {l: {} for l in self.LEVELS}
        self._lock = threading.RLock()
    def record(self, timestamp: float, value: float):
        with self._lock:
            for level in self.LEVELS:
                key = self._format_key(timestamp, level)
                if key not in self._buckets[level]:
                    self._buckets[level][key] = TimeBucket(level=level, key=key)
                self._buckets[level][key].update(value)
    def _format_key(self, ts: float, level: str) -> str:
        import time as tm
        t = tm.gmtime(ts)
        if level == "second": return tm.strftime("%Y-%m-%dT%H:%M:%S", t)
        elif level == "minute": return tm.strftime("%Y-%m-%dT%H:%M", t)
        elif level == "hour": return tm.strftime("%Y-%m-%dT%H", t)
        elif level == "day": return tm.strftime("%Y-%m-%d", t)
        elif level == "week": return tm.strftime("%Y-W%W", t)
        elif level == "month": return tm.strftime("%Y-%m", t)
        return ""
    def rollup(self, from_level: str, to_level: str) -> Dict[str, TimeBucket]:
        result = {}
        idx = self.LEVELS.index(from_level)
        tgt_idx = self.LEVELS.index(to_level)
        for key, bucket in self._buckets[from_level].items():
            parent_key = "-".join(key.split("-")[:tgt_idx + 1])
            if parent_key not in result:
                result[parent_key] = TimeBucket(level=to_level, key=parent_key)
            result[parent_key].sum_value += bucket.sum_value
            result[parent_key].count += bucket.count
            result[parent_key].min_value = min(result[parent_key].min_value, bucket.min_value)
            result[parent_key].max_value = max(result[parent_key].max_value, bucket.max_value)
        return result
    def get_buckets(self, level: str) -> List[TimeBucket]:
        return list(self._buckets.get(level, {}).values())
    def query_range(self, level: str, start_key: str, end_key: str) -> List[TimeBucket]:
        buckets = self._buckets.get(level, {})
        return [b for k, b in sorted(buckets.items()) if start_key <= k <= end_key]

class HierarchicalAggregator:
    def __init__(self):
        self.time_hierarchy = TimeHierarchy()
    def ingest(self, timestamp: float, value: float, dimensions: Dict = None):
        self.time_hierarchy.record(timestamp, value)
    def drill_down(self, current_level: str, key: str) -> Dict:
        idx = TimeHierarchy.LEVELS.index(current_level)
        if idx >= len(TimeHierarchy.LEVELS) - 1:
            return {}
        next_level = TimeHierarchy.LEVELS[idx + 1]
        children = self.time_hierarchy.get_buckets(next_level)
        return {b.key: b for b in children if b.key.startswith(key)}
    def roll_up(self, from_level: str, to_level: str) -> Dict:
        return self.time_hierarchy.rollup(from_level, to_level)
