"""Distributed Cache Layer"""
from __future__ import annotations
import time, json, threading, logging
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("infrastructure.storage.cache")

class CachePolicy(str):
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"

class CacheEntry:
    def __init__(self, key: str, value: Any, ttl: float = 300):
        self.key = key
        self.value = value
        self.created = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_access = time.time()
    def is_expired(self) -> bool:
        return time.time() - self.created > self.ttl
    def touch(self):
        self.access_count += 1
        self.last_access = time.time()

class MemoryCache:
    def __init__(self, max_size: int = 1000, policy: str = "lru"):
        self.max_size = max_size
        self.policy = policy
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                if entry.is_expired():
                    del self._cache[key]
                    return None
                entry.touch()
                self._cache.move_to_end(key)
                return entry.value
            return None
    def set(self, key: str, value: Any, ttl: float = 300):
        with self._lock:
            if len(self._cache) >= self.max_size:
                self._evict()
            self._cache[key] = CacheEntry(key, value, ttl)
    def _evict(self):
        if not self._cache:
            return
        if self.policy == "lru":
            self._cache.popitem(last=False)
        elif self.policy == "lfu":
            evict_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
            del self._cache[evict_key]
        else:
            self._cache.popitem(last=False)
    def clear(self):
        with self._lock:
            self._cache.clear()
    def get_stats(self) -> Dict:
        return {"size": len(self._cache), "max_size": self.max_size, "policy": self.policy}
