"""MemoryManager — 持久化记忆管理(项目/会话/偏好)"""
from __future__ import annotations
import time, json, os, logging, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("agent_core.memory_manager")

class MemoryLevel(str, Enum):
    EPHEMERAL = "ephemeral"
    SESSION = "session"
    PROJECT = "project"
    PERSISTENT = "persistent"

@dataclass
class MemoryItem:
    key: str = ""
    content: str = ""
    level: MemoryLevel = MemoryLevel.SESSION
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0

class MemoryManager:
    """记忆管理器 — 多层级记忆存储与检索"""
    
    def __init__(self, persist_dir: str = ""):
        if not persist_dir:
            persist_dir = os.path.expanduser("~/.laap/memory")
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        self._items: Dict[str, MemoryItem] = {}
        self._lock = threading.RLock()
        self._load()
    
    def _load(self):
        path = os.path.join(self.persist_dir, "memory.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data:
                    self._items[item["key"]] = MemoryItem(**item)
            except: pass
    
    def save(self):
        path = os.path.join(self.persist_dir, "memory.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump([vars(item) for item in self._items.values() if item.level != MemoryLevel.EPHEMERAL],
                     f, ensure_ascii=False, indent=2, default=str)
    
    def store(self, key: str, content: str, level: MemoryLevel = MemoryLevel.SESSION,
              tags: List[str] = None, importance: float = 0.5):
        with self._lock:
            self._items[key] = MemoryItem(key=key, content=content, level=level,
                                         tags=tags or [], importance=importance)
            if level != MemoryLevel.EPHEMERAL:
                self.save()
    
    def recall(self, key: str) -> Optional[str]:
        with self._lock:
            item = self._items.get(key)
            if item:
                item.last_accessed = time.time()
                item.access_count += 1
                return item.content
            return None
    
    def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        query_lower = query.lower()
        results = []
        with self._lock:
            for item in self._items.values():
                score = 0
                if query_lower in item.key.lower(): score += 10
                if query_lower in item.content.lower(): score += 5
                for tag in item.tags:
                    if query_lower in tag.lower(): score += 3
                score *= item.importance
                if score > 0:
                    results.append((score, item))
        results.sort(key=lambda x: -x[0])
        return [item for _, item in results[:limit]]
    
    def get_stats(self) -> dict:
        with self._lock:
            levels = {}
            for item in self._items.values():
                levels[item.level.value] = levels.get(item.level.value, 0) + 1
            return {"total": len(self._items), "levels": levels}
